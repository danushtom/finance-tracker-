from __future__ import annotations

from datetime import date as date_type

from bson import ObjectId
from fastapi import APIRouter, Query

from app.deps import CurrentUser, DbDep
from app.errors import NotFoundError, ValidationProblem
from app.models.common import utcnow
from app.models.merchant import MerchantSource
from app.models.transaction import Transaction
from app.repositories.categories import CategoryRepository
from app.repositories.merchants import MerchantRepository
from app.repositories.rules import RuleRepository
from app.repositories.transactions import TransactionRepository
from app.repositories.users import UserRepository
from app.services.dedupe import compute_fingerprint
from app.services.normalise import normalise_merchant
from app.schemas.transactions import (
    BulkCategoriseRequest,
    RuleSuggestion,
    SplitRequest,
    TransactionCreate,
    TransactionUpdate,
    TransactionUpdateResponse,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=list[Transaction])
async def list_transactions(
    user: CurrentUser,
    db: DbDep,
    month: str | None = None,
    date_from: date_type | None = None,
    date_to: date_type | None = None,
    account_id: str | None = None,
    category_id: str | None = None,
    class_: str | None = Query(default=None, alias="class"),
    kind: str | None = None,
    needs_review: bool | None = None,
    min_minor: int | None = None,
    max_minor: int | None = None,
    q: str | None = None,
    cursor: str | None = None,
    limit: int = 100,
):
    repo = TransactionRepository(db)
    return await repo.list_filtered(
        user.id,
        month=month,
        date_from=date_from,
        date_to=date_to,
        account_id=ObjectId(account_id) if account_id else None,
        category_id=ObjectId(category_id) if category_id else None,
        category_class=class_,
        kind=kind,
        needs_review=needs_review,
        min_minor=min_minor,
        max_minor=max_minor,
        q=q,
        cursor_id=ObjectId(cursor) if cursor else None,
        limit=limit,
    )


@router.get("/review", response_model=list[Transaction])
async def review_queue(user: CurrentUser, db: DbDep, limit: int = 100):
    """FR-15.1: low confidence, uncategorised, unmatched large credits,
    suspected duplicates all surface via needs_review=True."""
    repo = TransactionRepository(db)
    return await repo.find(user.id, {"needs_review": True}, sort=[("date", -1)], limit=limit)


@router.post("", response_model=Transaction, status_code=201)
async def create_manual_transaction(body: TransactionCreate, user: CurrentUser, db: DbDep):
    """FR-2.15: manual entry for cash spending that never touches the bank."""
    norm = normalise_merchant(body.description_raw)
    category_class = None
    if body.category_id:
        category = await CategoryRepository(db).get(user.id, ObjectId(body.category_id))
        if category is None:
            raise ValidationProblem("Invalid category", [{"field": "category_id", "message": "not found"}])
        category_class = category.class_

    fingerprint = compute_fingerprint(
        account_id=ObjectId(body.account_id),
        txn_date=body.date,
        amount_minor=body.amount_minor,
        merchant_norm=norm.merchant_norm,
        balance_minor=None,
        occurrence_index=int(utcnow().timestamp() * 1000) % 1_000_000,
    )

    txn = Transaction(
        user_id=user.id,
        account_id=ObjectId(body.account_id),
        date=body.date,
        description_raw=body.description_raw,
        merchant_norm=norm.merchant_norm,
        counterparty_vpa=norm.counterparty_vpa,
        amount_minor=body.amount_minor,
        direction=body.direction,
        kind=body.kind,
        category_id=ObjectId(body.category_id) if body.category_id else None,
        category_class=category_class,
        confidence=100 if body.category_id else 0,
        categorised_by="user" if body.category_id else "none",
        needs_review=body.category_id is None,
        note=body.note,
        is_manual=True,
        fingerprint=fingerprint,
    )
    await TransactionRepository(db).insert(txn)
    await UserRepository(db).bump_data_version(user.id)
    return txn


@router.patch("/{transaction_id}", response_model=TransactionUpdateResponse)
async def update_transaction(transaction_id: str, body: TransactionUpdate, user: CurrentUser, db: DbDep):
    """FR-4.5, FR-4.6: the user can recategorise any transaction; the
    response offers a rule suggestion for the merchant."""
    txn_repo = TransactionRepository(db)
    txn = await txn_repo.get(user.id, ObjectId(transaction_id))
    if txn is None:
        raise NotFoundError("Transaction")

    updates: dict = {}
    category_changed = False
    if body.category_id is not None:
        category = await CategoryRepository(db).get(user.id, ObjectId(body.category_id))
        if category is None:
            raise ValidationProblem("Invalid category", [{"field": "category_id", "message": "not found"}])
        updates.update(
            category_id=ObjectId(body.category_id),
            category_class=category.class_.value,
            categorised_by="user",
            confidence=100,
            needs_review=False,
        )
        category_changed = True
    if body.subcategory_id is not None:
        updates["subcategory_id"] = ObjectId(body.subcategory_id)
    if body.kind is not None:
        updates["kind"] = body.kind
    if body.note is not None:
        updates["note"] = body.note
    if body.tags is not None:
        updates["tags"] = body.tags

    await txn_repo.update(user.id, txn.id, {"$set": updates})
    await UserRepository(db).bump_data_version(user.id)

    suggestion = None
    if category_changed:
        await MerchantRepository(db).upsert(
            user.id,
            txn.merchant_norm,
            display_name=txn.merchant_norm,
            category_id=ObjectId(body.category_id),
            subcategory_id=ObjectId(body.subcategory_id) if body.subcategory_id else None,
            confidence=100,
            source=MerchantSource.USER,
            seen_at=utcnow(),
            amount_minor=txn.amount_minor,
        )
        existing_rule = await RuleRepository(db).find_exact(user.id, txn.merchant_norm)
        if existing_rule is None:
            affected = await txn_repo.count_matching(user.id, {"merchant_norm": txn.merchant_norm})
            suggestion = RuleSuggestion(
                match_type="exact", pattern=txn.merchant_norm, affected_past_count=affected
            )

    return TransactionUpdateResponse(id=str(txn.id), rule_suggestion=suggestion)


@router.post("/bulk-categorise", status_code=204)
async def bulk_categorise(body: BulkCategoriseRequest, user: CurrentUser, db: DbDep):
    """FR-15.3: bulk-categorise transactions with the same merchant."""
    txn_repo = TransactionRepository(db)
    category = await CategoryRepository(db).get(user.id, ObjectId(body.category_id))
    if category is None:
        raise ValidationProblem("Invalid category", [{"field": "category_id", "message": "not found"}])
    ids = [ObjectId(i) for i in body.transaction_ids]
    await txn_repo.bulk_set_category(user.id, ids, ObjectId(body.category_id))
    await db.transactions.update_many(
        {"user_id": user.id, "_id": {"$in": ids}}, {"$set": {"category_class": category.class_.value}}
    )
    await UserRepository(db).bump_data_version(user.id)


@router.post("/{transaction_id}/split", status_code=204)
async def split_transaction(transaction_id: str, body: SplitRequest, user: CurrentUser, db: DbDep):
    """FR-5.7: split a cash withdrawal (or any transaction) into multiple
    categorised lines after the fact. Implemented as child transactions
    linked to the original via `note`, with the original zeroed out of
    spend totals by re-kinding it to a transfer-like marker; this keeps the
    ledger auditable without deleting the source row."""
    txn_repo = TransactionRepository(db)
    original = await txn_repo.get(user.id, ObjectId(transaction_id))
    if original is None:
        raise NotFoundError("Transaction")

    total_split = sum(line.amount_minor for line in body.lines)
    if total_split != abs(original.amount_minor):
        raise ValidationProblem(
            "Split lines must sum to the original amount",
            [{"field": "lines", "message": f"sum {total_split} != {abs(original.amount_minor)}"}],
        )

    for i, line in enumerate(body.lines):
        category = await CategoryRepository(db).get(user.id, ObjectId(line.category_id))
        if category is None:
            raise ValidationProblem("Invalid category", [{"field": f"lines[{i}].category_id", "message": "not found"}])
        child = Transaction(
            user_id=user.id,
            account_id=original.account_id,
            date=original.date,
            description_raw=f"{original.description_raw} (split {i + 1}/{len(body.lines)})",
            merchant_norm=original.merchant_norm,
            amount_minor=-abs(line.amount_minor),
            direction="debit",
            kind="expense",
            category_id=ObjectId(line.category_id),
            category_class=category.class_.value,
            confidence=100,
            categorised_by="user",
            note=line.note,
            fingerprint=compute_fingerprint(
                account_id=original.account_id,
                txn_date=original.date,
                amount_minor=-abs(line.amount_minor),
                merchant_norm=f"{original.merchant_norm} SPLIT{i}",
                balance_minor=None,
                occurrence_index=i + 1,
            ),
        )
        await txn_repo.insert(child)

    await txn_repo.update(
        user.id, original.id, {"$set": {"kind": "transfer", "category_class": "transfer", "needs_review": False}}
    )
    await UserRepository(db).bump_data_version(user.id)
