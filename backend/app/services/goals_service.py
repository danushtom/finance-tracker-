"""Goal progress and the default Emergency Fund goal (FR-10.5, FR-10.6)."""

from __future__ import annotations

import statistics
from datetime import date

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.common import Minor
from app.models.goal import Goal
from app.models.user import User
from app.repositories.goals import GoalRepository
from app.repositories.transactions import TransactionRepository


def compute_progress(goal: Goal, *, today: date | None = None) -> dict:
    today = today or date.today()
    percentage = 0.0
    if goal.target_amount_minor > 0:
        percentage = min(100.0, 100.0 * goal.current_amount_minor / goal.target_amount_minor)

    on_track: str | None = None
    required_monthly_minor: Minor | None = None
    if goal.target_date and goal.target_date > today:
        months_left = max(1, (goal.target_date.year - today.year) * 12 + (goal.target_date.month - today.month))
        remaining = max(0, goal.target_amount_minor - goal.current_amount_minor)
        required_monthly_minor = remaining // months_left if months_left else remaining
        if goal.monthly_reservation_minor >= required_monthly_minor:
            on_track = "ahead" if goal.monthly_reservation_minor > required_monthly_minor else "on_track"
        else:
            on_track = "behind"

    return {"percentage": percentage, "on_track": on_track, "required_monthly_minor": required_monthly_minor}


async def median_monthly_essential_expenses(
    db: AsyncIOMotorDatabase, user_id, *, months_back: int = 6  # noqa: ANN001
) -> Minor:
    """fixed + median variable, over up to the last N months of history —
    the basis for the default Emergency Fund target (FR-10.6)."""
    txn_repo = TransactionRepository(db)
    today = date.today()
    months = []
    year, month = today.year, today.month
    for _ in range(months_back):
        months.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            month, year = 12, year - 1

    fixed_totals = [await txn_repo.sum_outflows(user_id, m, class_="fixed") for m in months]
    variable_totals = [await txn_repo.sum_outflows(user_id, m, class_in=["variable", "isolated"]) for m in months]
    fixed = statistics.median(fixed_totals) if fixed_totals else 0
    variable = statistics.median(variable_totals) if variable_totals else 0
    return int(fixed + variable)


async def ensure_emergency_fund_goal(db: AsyncIOMotorDatabase, user: User) -> Goal:
    """Created by default at 6x median monthly essential expenses,
    recalculated as data accumulates (FR-10.6). Idempotent: updates the
    existing emergency-fund goal's target rather than duplicating it."""
    goal_repo = GoalRepository(db)
    existing = await goal_repo.find(user.id, {"is_emergency_fund": True}, limit=1)

    median_essential = await median_monthly_essential_expenses(db, user.id)
    target = median_essential * 6

    if existing:
        goal = existing[0]
        if target and target != goal.target_amount_minor:
            await goal_repo.update(user.id, goal.id, {"$set": {"target_amount_minor": target}})
            goal.target_amount_minor = target
        return goal

    goal = Goal(
        user_id=user.id,
        name="Emergency Fund",
        target_amount_minor=target,
        priority="high",
        is_emergency_fund=True,
    )
    await goal_repo.insert(goal)
    return goal
