from __future__ import annotations

from datetime import date

from fastapi import APIRouter

from app.deps import CurrentUser, DbDep
from app.services.dashboard_service import build_dashboard, get_safe_to_spend_cached

router = APIRouter(tags=["dashboard"])


def _current_month() -> str:
    today = date.today()
    return f"{today.year:04d}-{today.month:02d}"


@router.get("/dashboard")
async def get_dashboard(user: CurrentUser, db: DbDep, month: str | None = None):
    payload = await build_dashboard(db, user, month or _current_month())
    return payload


@router.get("/safe-to-spend")
async def get_safe_to_spend(user: CurrentUser, db: DbDep, month: str | None = None):
    """FR-8.2 contract: `{ amount_minor, is_over, per_day_minor, days_left, lines[] }`."""
    sts = await get_safe_to_spend_cached(db, user, month or _current_month())
    return {
        "month": sts.month,
        "amount_minor": sts.display_amount_minor(),
        "is_over": sts.is_over,
        "over_by_minor": sts.over_by_minor(),
        "per_day_minor": sts.per_day_minor,
        "days_left": sts.days_left,
        "lines": [
            {"label": l.label, "amount_minor": l.amount_minor, "sign": l.sign, "drilldown": l.drilldown}
            for l in sts.lines
        ],
    }
