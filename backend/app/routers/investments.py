from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter

from app.deps import CurrentUser, DbDep
from app.errors import NotFoundError
from app.models.investment import Investment
from app.repositories.goals import GoalRepository
from app.repositories.investments import InvestmentRepository
from app.repositories.users import UserRepository
from app.schemas.investments import InvestmentCreate, InvestmentUpdate

router = APIRouter(prefix="/investments", tags=["investments"])

# FR-14.3: a sequence, not a recommendation set. FR-14.4/FR-14.5: general
# principles only, never a specific fund/stock/product (SEBI/AMFI-style
# investor education framing).
_STAGE_GUIDANCE = {
    "emergency_fund": (
        "Build your emergency fund first — a cash buffer covering essential "
        "expenses protects the rest of your plan from a bad month."
    ),
    "diversified_investing": (
        "With an emergency fund in place, the general principle is diversified, "
        "long-term investing (e.g. via SIPs) rather than trying to time the market."
    ),
    "individual_stocks": (
        "Once diversified investing is established, some investors choose to "
        "allocate a small, deliberate portion to individual stocks — general "
        "information only, not a recommendation of any specific stock."
    ),
}


@router.get("")
async def list_investments(user: CurrentUser, db: DbDep):
    repo = InvestmentRepository(db)
    investments = await repo.find(user.id, {"archived": False})

    by_type: dict[str, int] = {}
    total_invested = 0
    total_current = 0
    for inv in investments:
        by_type[inv.type] = by_type.get(inv.type, 0) + inv.current_value_minor
        total_invested += inv.invested_minor
        total_current += inv.current_value_minor

    stage = await _determine_stage(db, user)

    return {
        "investments": investments,
        "allocation_by_type": by_type,
        "total_invested_minor": total_invested,
        "total_current_value_minor": total_current,
        "gain_loss_minor": total_current - total_invested,
        "stage": stage,
        "stage_guidance": _STAGE_GUIDANCE[stage],
    }


async def _determine_stage(db, user) -> str:  # noqa: ANN001
    goal_repo = GoalRepository(db)
    investment_repo = InvestmentRepository(db)

    emergency_funds = await goal_repo.find(user.id, {"is_emergency_fund": True})
    ef_funded = bool(emergency_funds) and emergency_funds[0].current_amount_minor >= emergency_funds[0].target_amount_minor
    if not ef_funded:
        return "emergency_fund"

    investments = await investment_repo.find(user.id, {"archived": False})
    diversified_types = {"index_fund", "active_fund", "debt", "epf_ppf"}
    has_diversified = any(i.type in diversified_types for i in investments)
    if not has_diversified:
        return "diversified_investing"

    return "individual_stocks"


@router.post("", response_model=Investment, status_code=201)
async def create_investment(body: InvestmentCreate, user: CurrentUser, db: DbDep):
    investment = Investment(user_id=user.id, **body.model_dump())
    await InvestmentRepository(db).insert(investment)
    await UserRepository(db).bump_data_version(user.id)
    return investment


@router.patch("/{investment_id}", response_model=Investment)
async def update_investment(investment_id: str, body: InvestmentUpdate, user: CurrentUser, db: DbDep):
    repo = InvestmentRepository(db)
    updates = body.model_dump(exclude_unset=True)
    if not await repo.update(user.id, ObjectId(investment_id), {"$set": updates}):
        raise NotFoundError("Investment")
    await UserRepository(db).bump_data_version(user.id)
    return await repo.get(user.id, ObjectId(investment_id))
