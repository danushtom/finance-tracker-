from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter

from app.deps import CurrentUser, DbDep
from app.errors import NotFoundError, ValidationProblem
from app.models.income import IncomeSource
from app.repositories.income_sources import IncomeSourceRepository
from app.repositories.transactions import TransactionRepository
from app.repositories.users import UserRepository
from app.schemas.income import IncomeBreakdown, IncomeClassifyRequest, IncomeSourceCreate, IncomeSourceUpdate

router = APIRouter(prefix="/income", tags=["income"])


@router.get("-sources", response_model=list[IncomeSource])
async def list_income_sources(user: CurrentUser, db: DbDep):
    return await IncomeSourceRepository(db).find(user.id, {"active": True})


@router.post("-sources", response_model=IncomeSource, status_code=201)
async def create_income_source(body: IncomeSourceCreate, user: CurrentUser, db: DbDep):
    source = IncomeSource(user_id=user.id, **body.model_dump())
    await IncomeSourceRepository(db).insert(source)
    await UserRepository(db).bump_data_version(user.id)
    return source


@router.patch("-sources/{source_id}", response_model=IncomeSource)
async def update_income_source(source_id: str, body: IncomeSourceUpdate, user: CurrentUser, db: DbDep):
    repo = IncomeSourceRepository(db)
    updates = body.model_dump(exclude_unset=True)
    if not await repo.update(user.id, ObjectId(source_id), {"$set": updates}):
        raise NotFoundError("Income source")
    await UserRepository(db).bump_data_version(user.id)
    return await repo.get(user.id, ObjectId(source_id))


@router.get("", response_model=IncomeBreakdown)
async def income_breakdown(month: str, user: CurrentUser, db: DbDep):
    """FR-6.4: baseline and variable shown as visually distinct figures,
    never merged into a single headline."""
    txn_repo = TransactionRepository(db)
    baseline = await txn_repo.sum_income(user.id, month, income_type="baseline")
    variable = await txn_repo.sum_income(user.id, month, income_type="variable")
    return IncomeBreakdown(
        month=month,
        baseline_received_minor=baseline,
        variable_received_minor=variable,
        total_minor=baseline + variable,
    )


@router.post("/{txn_id}/classify", status_code=204)
async def classify_income(txn_id: str, body: IncomeClassifyRequest, user: CurrentUser, db: DbDep):
    """FR-6.2: user answers "Is this baseline or variable income?" for an
    unmatched credit."""
    txn_repo = TransactionRepository(db)
    txn = await txn_repo.get(user.id, ObjectId(txn_id))
    if txn is None:
        raise NotFoundError("Transaction")

    updates: dict = {"needs_review": False}
    if body.source_id:
        source = await IncomeSourceRepository(db).get(user.id, ObjectId(body.source_id))
        if source is None:
            raise ValidationProblem("Invalid income source", [{"field": "source_id", "message": "not found"}])
        updates["income_source_id"] = source.id
    elif body.type:
        # No specific source — create an ad-hoc source of this type so the
        # credit (and future ones from the same merchant) aggregate
        # correctly without forcing the user to name it up front.
        source_repo = IncomeSourceRepository(db)
        existing_sources = await source_repo.find(user.id, {"match_patterns": txn.merchant_norm})
        adhoc = existing_sources[0] if existing_sources else None
        if adhoc is None:
            adhoc = IncomeSource(
                user_id=user.id, name=txn.merchant_norm, type=body.type, match_patterns=[txn.merchant_norm]
            )
            await source_repo.insert(adhoc)
        updates["income_source_id"] = adhoc.id
    else:
        raise ValidationProblem("source_id or type is required", [{"field": "source_id", "message": "required"}])

    await txn_repo.update(user.id, txn.id, {"$set": updates})
    await UserRepository(db).bump_data_version(user.id)
