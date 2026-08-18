from __future__ import annotations

# Imported under an alias: a field literally named `date` (in
# GoalContribution below) would otherwise shadow this type name when
# pydantic evaluates the `from __future__ import annotations` string
# annotations against the class namespace, raising a TypeError at class
# creation time.
from datetime import date as _date

from pydantic import BaseModel

from app.models.common import Minor


class GoalCreate(BaseModel):
    name: str
    target_amount_minor: Minor
    current_amount_minor: Minor = 0
    target_date: _date | None = None
    priority: str = "medium"
    linked_account_id: str | None = None
    monthly_reservation_minor: Minor = 0


class GoalUpdate(BaseModel):
    name: str | None = None
    target_amount_minor: Minor | None = None
    target_date: _date | None = None
    priority: str | None = None
    monthly_reservation_minor: Minor | None = None
    status: str | None = None


class GoalContribution(BaseModel):
    amount_minor: Minor
    date: _date | None = None
    transaction_id: str | None = None


class GoalProgress(BaseModel):
    percentage: float
    on_track: str | None  # "ahead" | "on_track" | "behind" | None (no target date)
    required_monthly_minor: Minor | None
