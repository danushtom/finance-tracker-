from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter

from app.deps import CurrentUser, DbDep
from app.errors import NotFoundError, ValidationProblem
from app.models.allocation import Allocation
from app.repositories.allocations import AllocationRepository
from app.repositories.transactions import TransactionRepository
from app.repositories.users import UserRepository
from app.schemas.allocations import AllocationCreate, AllocationOverride
from app.services.allocation import propose_allocation

router = APIRouter(prefix="/allocations", tags=["allocations"])


@router.get("", response_model=list[Allocation])
async def list_allocations(user: CurrentUser, db: DbDep, month: str | None = None):
    repo = AllocationRepository(db)
    return await repo.find(user.id, {"month": month} if month else None, sort=[("created_at", -1)])


@router.post("", response_model=Allocation, status_code=201)
async def create_allocation(body: AllocationCreate, user: CurrentUser, db: DbDep):
    """FR-12.1: propose a split for a variable-income credit."""
    txn_repo = TransactionRepository(db)
    allocation_repo = AllocationRepository(db)
    txn = await txn_repo.get(user.id, ObjectId(body.transaction_id))
    if txn is None:
        raise NotFoundError("Transaction")
    if txn.kind != "income" or txn.direction != "credit":
        raise ValidationProblem("Not an income credit", [{"field": "transaction_id", "message": "must be an income credit"}])

    existing = await allocation_repo.get_by_transaction(user.id, txn.id)
    if existing:
        return existing

    return await propose_allocation(
        db,
        user_id=user.id,
        transaction_id=txn.id,
        month=txn.date.strftime("%Y-%m"),
        amount_minor=txn.amount_minor,
        split=user.settings.variable_split,
    )


@router.patch("/{allocation_id}", response_model=Allocation)
async def override_allocation(allocation_id: str, body: AllocationOverride, user: CurrentUser, db: DbDep):
    """FR-12.3: override any proposed split; the original recommendation is
    kept visible (the `proposed_*` fields are never overwritten)."""
    repo = AllocationRepository(db)
    updates = {
        "override_invest_minor": body.invest_minor,
        "override_goals_minor": body.goals_minor,
        "override_discretionary_minor": body.discretionary_minor,
    }
    if not await repo.update(user.id, ObjectId(allocation_id), {"$set": updates}):
        raise NotFoundError("Allocation")
    await UserRepository(db).bump_data_version(user.id)
    return await repo.get(user.id, ObjectId(allocation_id))
