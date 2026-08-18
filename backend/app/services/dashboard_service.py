"""Dashboard aggregation (FR-8.1) — one call, one payload (NFR-1), backed by
the version-based derived cache (FR-8.3.6, ADR-5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.common import Minor
from app.models.user import User
from app.repositories.categories import CategoryRepository
from app.repositories.commitments import CommitmentRepository
from app.repositories.derived_cache import DerivedCacheRepository
from app.repositories.goals import GoalRepository
from app.repositories.transactions import TransactionRepository
from app.repositories.wishlist import WishlistRepository
from app.services.safe_to_spend import SafeToSpend, WaterfallLine, compute_safe_to_spend


@dataclass
class DashboardPayload:
    month: str
    baseline_income_minor: Minor
    variable_income_minor: Minor
    spent_minor: Minor
    saved_minor: Minor
    invested_minor: Minor
    available_minor: Minor
    safe_to_spend: dict
    isolated: list[dict]
    fixed_due_minor: Minor
    fixed_paid_minor: Minor
    fixed_commitments: list[dict]
    category_breakdown: list[dict]
    review_queue_count: int
    top_goals: list[dict]
    top_wishlist: list[dict]


def _sts_to_dict(sts: SafeToSpend) -> dict:
    return {
        "month": sts.month,
        "amount_minor": sts.display_amount_minor(),
        "raw_amount_minor": sts.amount_minor,
        "is_over": sts.is_over,
        "over_by_minor": sts.over_by_minor(),
        "per_day_minor": sts.per_day_minor,
        "days_left": sts.days_left,
        "lines": [
            {"label": l.label, "amount_minor": l.amount_minor, "sign": l.sign, "drilldown": l.drilldown}
            for l in sts.lines
        ],
    }


async def get_safe_to_spend_cached(db: AsyncIOMotorDatabase, user: User, month: str) -> SafeToSpend:
    cache = DerivedCacheRepository(db)
    key = f"sts:{month}"
    cached = await cache.get(user.id, key, user.data_version)
    if cached is not None:
        lines = [WaterfallLine(**line) for line in cached["lines"]]
        return SafeToSpend(
            month=cached["month"],
            amount_minor=cached["raw_amount_minor"],
            is_over=cached["is_over"],
            per_day_minor=cached["per_day_minor"],
            days_left=cached["days_left"],
            lines=lines,
        )

    sts = await compute_safe_to_spend(db, user, month)
    await cache.put(user.id, key, user.data_version, _sts_to_dict(sts))
    return sts


async def build_dashboard(db: AsyncIOMotorDatabase, user: User, month: str) -> DashboardPayload:
    txn_repo = TransactionRepository(db)
    category_repo = CategoryRepository(db)
    commitment_repo = CommitmentRepository(db)
    goal_repo = GoalRepository(db)
    wishlist_repo = WishlistRepository(db)

    sts = await get_safe_to_spend_cached(db, user, month)

    baseline = await txn_repo.sum_income(user.id, month, income_type="baseline")
    variable = await txn_repo.sum_income(user.id, month, income_type="variable")

    spent = await txn_repo.sum_outflows(user.id, month, class_in=["fixed", "variable", "isolated"])
    invested = await txn_repo.sum_outflows(user.id, month, class_="investment")

    goals = await goal_repo.list_active(user.id)
    saved = 0
    for g in goals:
        saved += sum(c.amount_minor for c in g.contributions if c.date.strftime("%Y-%m") == month)

    categories = {c.id: c for c in await category_repo.find(user.id)}
    breakdown_raw = await txn_repo.category_breakdown(user.id, month)
    category_breakdown = [
        {
            "category_id": str(row["_id"]["cat"]) if row["_id"]["cat"] else None,
            "category_name": categories[row["_id"]["cat"]].name if row["_id"]["cat"] in categories else "Uncategorised",
            "class": row["_id"]["cls"],
            "total_minor": abs(row["total"]),
            "count": row["count"],
        }
        for row in breakdown_raw
    ]

    isolated = [row for row in category_breakdown if row["class"] == "isolated"]

    confirmed = await commitment_repo.list_confirmed(user.id)
    fixed_due = sum(c.expected_amount_minor for c in confirmed)
    fixed_paid = await txn_repo.sum_outflows(user.id, month, class_="fixed")

    review_count = await txn_repo.count(user.id, {"needs_review": True})

    top_goals = sorted(goals, key=lambda g: {"high": 0, "medium": 1, "low": 2}.get(g.priority, 3))[:3]
    wishlist_items = await wishlist_repo.find(user.id, {"status": "wanted"})
    top_wishlist = sorted(wishlist_items, key=lambda w: {"high": 0, "medium": 1, "low": 2}.get(w.priority, 3))[:3]

    return DashboardPayload(
        month=month,
        baseline_income_minor=baseline,
        variable_income_minor=variable,
        spent_minor=spent,
        saved_minor=saved,
        invested_minor=invested,
        available_minor=sts.display_amount_minor(),
        safe_to_spend=_sts_to_dict(sts),
        isolated=isolated,
        fixed_due_minor=fixed_due,
        fixed_paid_minor=fixed_paid,
        fixed_commitments=[
            {
                "id": str(c.id),
                "display_name": c.display_name,
                "expected_amount_minor": c.expected_amount_minor,
                "next_expected_date": c.next_expected_date.isoformat() if c.next_expected_date else None,
            }
            for c in confirmed
        ],
        category_breakdown=category_breakdown,
        review_queue_count=review_count,
        top_goals=[
            {
                "id": str(g.id),
                "name": g.name,
                "target_amount_minor": g.target_amount_minor,
                "current_amount_minor": g.current_amount_minor,
                "priority": g.priority,
            }
            for g in top_goals
        ],
        top_wishlist=[
            {"id": str(w.id), "name": w.name, "price_minor": w.price_minor, "priority": w.priority}
            for w in top_wishlist
        ],
    )
