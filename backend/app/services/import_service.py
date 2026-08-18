"""Import orchestration: parse -> normalise -> dedupe -> categorise -> persist
(section 2.3, section 7). The HTTP layer only creates the `imports` doc and
enqueues a job; all of this runs in the worker (`app.worker.handlers`).
"""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path
from uuid import uuid4

import structlog
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.categorise.engine import apply_amount_conditional_override, categorise_merchants
from app.categorise.llm.factory import get_llm_provider
from app.config import Settings
from app.models.account import Account
from app.models.common import utcnow
from app.models.import_job import Import, ImportError as ImportRowError, ImportStatus, ImportSummary
from app.models.merchant import MerchantSource
from app.models.transaction import Transaction
from app.parsers import select_parser
from app.parsers.base import ColumnMapping, RawRow
from app.parsers.money import parse_statement_date, to_minor
from app.repositories.accounts import AccountRepository
from app.repositories.categories import CategoryRepository
from app.repositories.imports import ImportRepository
from app.repositories.income_sources import IncomeSourceRepository
from app.repositories.llm_cache import LLMCacheRepository
from app.repositories.merchants import MerchantRepository
from app.repositories.rules import RuleRepository
from app.repositories.transactions import TransactionRepository
from app.repositories.users import UserRepository
from app.services.dedupe import assign_fingerprints
from app.services.income_service import match_income_source
from app.services.normalise import normalise_merchant

log = structlog.get_logger(__name__)

# FR-6.2: unmatched credits at or above this amount prompt the user to
# classify the income as baseline or variable; smaller unmatched credits
# (refunds, small transfers) don't need that interruption.
UNMATCHED_INCOME_REVIEW_THRESHOLD_MINOR = 500_000  # ₹5,000


async def save_upload(
    settings: Settings, user_id: ObjectId, import_id: ObjectId, filename: str, content: bytes
) -> tuple[str, str]:
    """Writes the file outside the web root under a random-ish path keyed by
    user and import id (section 13 Security: never served statically)."""
    ext = Path(filename).suffix.lower()
    directory = Path(settings.storage_dir) / str(user_id)
    directory.mkdir(parents=True, exist_ok=True)
    stored_path = directory / f"{import_id}{ext}"
    stored_path.write_bytes(content)
    sha256 = hashlib.sha256(content).hexdigest()
    return str(stored_path), sha256


async def create_import(
    db: AsyncIOMotorDatabase,
    *,
    user_id: ObjectId,
    account_id: ObjectId,
    filename: str,
    mime: str,
    content: bytes,
) -> Import:
    import_doc = Import(
        user_id=user_id,
        account_id=account_id,
        filename=filename,
        stored_path="",
        mime=mime,
        size_bytes=len(content),
        sha256="",
        status=ImportStatus.QUEUED,
    )
    await ImportRepository(db).insert(import_doc)
    return import_doc


def _raw_amount(row: RawRow) -> tuple[int, str] | None:
    """Returns (signed_amount_minor, direction) or None if unparseable."""
    if row.amount is not None and row.amount.strip():
        minor = to_minor(row.amount)
        if minor is None:
            return None
        return minor, ("debit" if minor < 0 else "credit")
    debit = to_minor(row.debit) if row.debit else None
    credit = to_minor(row.credit) if row.credit else None
    if debit:
        return -abs(debit), "debit"
    if credit:
        return abs(credit), "credit"
    return None


async def run_import(
    db: AsyncIOMotorDatabase,
    settings: Settings,
    import_doc: Import,
    *,
    mapping: ColumnMapping | None = None,
) -> Import:
    import_repo = ImportRepository(db)
    txn_repo = TransactionRepository(db)
    account_repo = AccountRepository(db)
    category_repo = CategoryRepository(db)
    rule_repo = RuleRepository(db)
    merchant_repo = MerchantRepository(db)
    user_repo = UserRepository(db)
    llm_cache_repo = LLMCacheRepository(db)
    income_source_repo = IncomeSourceRepository(db)

    user = await user_repo.get_by_id(import_doc.user_id)
    account = await account_repo.get(import_doc.user_id, import_doc.account_id)
    if user is None or account is None:
        raise RuntimeError("Import references a missing user or account")

    await import_repo.update(
        import_doc.user_id, import_doc.id, {"$set": {"status": ImportStatus.PARSING.value, "started_at": utcnow()}}
    )

    path = Path(import_doc.stored_path)
    parser, parser_name = select_parser(path)
    mapping = mapping or (
        ColumnMapping.from_dict(account.column_mapping) if account.column_mapping else None
    )

    preview = parser.preview(path)
    if mapping is None and preview.needs_mapping:
        await import_repo.update(
            import_doc.user_id,
            import_doc.id,
            {
                "$set": {
                    "status": ImportStatus.NEEDS_MAPPING.value,
                    "parser": parser_name,
                    "preview": [dict(zip(preview.headers, r)) for r in preview.rows] if preview.headers else [],
                }
            },
        )
        return await import_repo.get(import_doc.user_id, import_doc.id)  # type: ignore[return-value]

    raw_rows = list(parser.parse(path, mapping=mapping))

    if len(raw_rows) > settings.max_upload_rows:
        await import_repo.update(
            import_doc.user_id,
            import_doc.id,
            {"$set": {"status": ImportStatus.FAILED.value, "finished_at": utcnow()}},
        )
        raise ValueError(f"Statement has {len(raw_rows)} rows, exceeding the {settings.max_upload_rows} limit")

    parsed: list[tuple[date, int, str, str | None, str, int | None]] = []
    errors: list[ImportRowError] = []
    for row in raw_rows:
        try:
            if not row.date or not row.description:
                raise ValueError("missing date or description")
            txn_date = parse_statement_date(row.date)
            amount_info = _raw_amount(row)
            if amount_info is None:
                raise ValueError("could not parse amount")
            amount_minor, direction = amount_info
            balance_minor = to_minor(row.balance) if row.balance else None
            norm = normalise_merchant(row.description)
            parsed.append((txn_date, amount_minor, direction, norm.counterparty_vpa, row.description, balance_minor))
        except Exception as exc:  # noqa: BLE001 - a bad row must not abort the whole import
            errors.append(ImportRowError(row=row.row_index, reason=str(exc)))

    fingerprints = assign_fingerprints(
        [(d, a, normalise_merchant(desc).merchant_norm, b) for d, a, _, _, desc, b in parsed],
        import_doc.account_id,
    )

    await import_repo.update(
        import_doc.user_id, import_doc.id, {"$set": {"status": ImportStatus.CATEGORISING.value}}
    )

    rules = await rule_repo.list_enabled(import_doc.user_id)
    income_sources = await income_source_repo.find(import_doc.user_id, {"active": True})
    merchant_norms = list({normalise_merchant(desc).merchant_norm for *_, desc, _ in parsed})
    llm_provider = get_llm_provider(user.settings.llm, settings)
    category_results = await categorise_merchants(
        user_id=import_doc.user_id,
        merchant_norms=merchant_norms,
        rules=rules,
        merchant_repo=merchant_repo,
        category_repo=category_repo,
        llm_cache_repo=llm_cache_repo,
        user_repo=user_repo,
        llm_provider=llm_provider,
        llm_monthly_call_cap=user.settings.llm.monthly_call_cap,
    )

    txns: list[Transaction] = []
    needs_review_count = 0
    llm_calls = 0
    for (txn_date, amount_minor, direction, vpa, desc, balance_minor), fingerprint in zip(parsed, fingerprints):
        norm = normalise_merchant(desc)
        result = category_results.get(norm.merchant_norm)
        if result is None:
            continue
        result = apply_amount_conditional_override(result, rules, norm.merchant_norm, direction, amount_minor)

        category = None
        if result.category_id:
            category = await category_repo.get(import_doc.user_id, result.category_id)

        threshold = user.settings.low_confidence_threshold
        needs_review = result.confidence < threshold
        if needs_review:
            needs_review_count += 1
        if result.categorised_by == "llm":
            llm_calls += 1

        kind = "income" if direction == "credit" and (category is None or category.class_.value == "income") else "expense"
        if category and category.class_.value == "transfer":
            kind = "transfer"
        elif category and category.class_.value == "investment":
            kind = "investment"

        income_source_id = None
        if kind == "income":
            matched_source = match_income_source(norm.merchant_norm, income_sources)
            if matched_source:
                income_source_id = matched_source.id
            elif abs(amount_minor) >= UNMATCHED_INCOME_REVIEW_THRESHOLD_MINOR and not needs_review:
                # FR-6.2: unmatched credits above a threshold prompt the user
                # via the review queue ("Is this baseline or variable income?").
                needs_review = True
                needs_review_count += 1

        txns.append(
            Transaction(
                user_id=import_doc.user_id,
                account_id=import_doc.account_id,
                import_id=import_doc.id,
                date=txn_date,
                description_raw=desc,
                merchant_norm=norm.merchant_norm,
                counterparty_vpa=vpa,
                amount_minor=amount_minor,
                direction=direction,
                balance_minor=balance_minor,
                kind=kind,
                category_id=result.category_id,
                subcategory_id=result.subcategory_id,
                category_class=category.class_ if category else None,
                income_source_id=income_source_id,
                confidence=result.confidence,
                categorised_by=result.categorised_by,
                needs_review=needs_review,
                fingerprint=fingerprint,
            )
        )

        if category is not None:
            await merchant_repo.upsert(
                import_doc.user_id,
                norm.merchant_norm,
                display_name=norm.merchant_norm,
                category_id=result.category_id,
                subcategory_id=result.subcategory_id,
                confidence=result.confidence,
                source=MerchantSource.LLM if result.categorised_by == "llm" else MerchantSource.SEED,
                seen_at=utcnow(),
                amount_minor=amount_minor,
            )

    inserted, duplicates = await txn_repo.insert_many_dedup(txns)

    dates = [t.date for t in txns]
    balances = [t.balance_minor for t in txns if t.balance_minor is not None]
    summary = ImportSummary(
        rows_found=len(raw_rows),
        imported=inserted,
        duplicates_skipped=duplicates,
        failed=len(errors),
        date_from=min(dates) if dates else None,
        date_to=max(dates) if dates else None,
        opening_balance_minor=balances[0] if balances else None,
        closing_balance_minor=balances[-1] if balances else None,
        llm_calls=llm_calls,
        needs_review_count=needs_review_count,
    )

    final_status = ImportStatus.NEEDS_REVIEW if needs_review_count else ImportStatus.COMPLETED
    await import_repo.update(
        import_doc.user_id,
        import_doc.id,
        {
            "$set": {
                "status": final_status.value,
                "parser": parser_name,
                "summary": summary.model_dump(mode="json"),
                "errors": [e.model_dump() for e in errors],
                "finished_at": utcnow(),
            }
        },
    )

    if mapping:
        await account_repo.update(import_doc.user_id, import_doc.account_id, {"$set": {"column_mapping": mapping.as_dict()}})

    if balances:
        await account_repo.update(
            import_doc.user_id,
            import_doc.account_id,
            {"$set": {"current_balance_minor": balances[-1], "balance_as_of": dates[-1]}},
        )

    await user_repo.bump_data_version(import_doc.user_id)
    log.info(
        "import_completed",
        import_id=str(import_doc.id),
        imported=inserted,
        duplicates=duplicates,
        needs_review=needs_review_count,
    )
    return await import_repo.get(import_doc.user_id, import_doc.id)  # type: ignore[return-value]


async def delete_import(db: AsyncIOMotorDatabase, user_id: ObjectId, import_id: ObjectId) -> int:
    """FR-2.14: deleting an import removes exactly the transactions it
    created, atomically (section 5.3 transaction usage #2)."""
    txn_repo = TransactionRepository(db)
    import_repo = ImportRepository(db)
    client = db.client
    async with await client.start_session() as session:
        async with session.start_transaction():
            deleted = await txn_repo.delete_by_import(user_id, import_id, session=session)
            await db.imports.delete_one({"user_id": user_id, "_id": import_id}, session=session)
    await UserRepository(db).bump_data_version(user_id)
    return deleted
