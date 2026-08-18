from __future__ import annotations

from datetime import date

from bson import ObjectId
from fastapi import APIRouter

from app.deps import CurrentUser, DbDep
from app.errors import NotFoundError
from app.models.common import utcnow
from app.models.goal import Contribution, Goal
from app.repositories.goals import GoalRepository
from app.repositories.users import UserRepository
from app.schemas.goals import GoalContribution, GoalCreate, GoalUpdate
from app.services.goals_service import compute_progress, ensure_emergency_fund_goal

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("")
async def list_goals(user: CurrentUser, db: DbDep, include_archived: bool = False):
    repo = GoalRepository(db)
    query = None if include_archived else {"status": {"$ne": "archived"}}
    goals = await repo.find(user.id, query, sort=[("created_at", 1)])
    return [{"goal": g, "progress": compute_progress(g)} for g in goals]


@router.post("", response_model=Goal, status_code=201)
async def create_goal(body: GoalCreate, user: CurrentUser, db: DbDep):
    data = body.model_dump()
    if data.get("linked_account_id"):
        data["linked_account_id"] = ObjectId(data["linked_account_id"])
    goal = Goal(user_id=user.id, **data)
    await GoalRepository(db).insert(goal)
    await UserRepository(db).bump_data_version(user.id)
    return goal


@router.post("/ensure-emergency-fund", response_model=Goal)
async def create_emergency_fund(user: CurrentUser, db: DbDep):
    goal = await ensure_emergency_fund_goal(db, user)
    await UserRepository(db).bump_data_version(user.id)
    return goal


@router.patch("/{goal_id}", response_model=Goal)
async def update_goal(goal_id: str, body: GoalUpdate, user: CurrentUser, db: DbDep):
    repo = GoalRepository(db)
    updates = body.model_dump(exclude_unset=True)
    if not await repo.update(user.id, ObjectId(goal_id), {"$set": updates}):
        raise NotFoundError("Goal")
    await UserRepository(db).bump_data_version(user.id)
    return await repo.get(user.id, ObjectId(goal_id))


@router.post("/{goal_id}/contribute", response_model=Goal)
async def contribute(goal_id: str, body: GoalContribution, user: CurrentUser, db: DbDep):
    """FR-10.3: record a contribution to a goal manually."""
    repo = GoalRepository(db)
    goal = await repo.get(user.id, ObjectId(goal_id))
    if goal is None:
        raise NotFoundError("Goal")

    contribution = Contribution(
        date=body.date or utcnow().date(),
        amount_minor=body.amount_minor,
        transaction_id=ObjectId(body.transaction_id) if body.transaction_id else None,
    )
    new_total = goal.current_amount_minor + body.amount_minor
    await repo.update(
        user.id,
        goal.id,
        {
            "$push": {"contributions": contribution.model_dump(mode="python")},
            "$set": {
                "current_amount_minor": new_total,
                "status": "achieved" if new_total >= goal.target_amount_minor else goal.status,
            },
        },
    )
    await UserRepository(db).bump_data_version(user.id)
    return await repo.get(user.id, goal.id)
