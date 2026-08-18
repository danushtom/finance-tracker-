from __future__ import annotations

from pydantic import BaseModel

from app.models.common import Minor, MongoDate, PyObjectId, UserScopedModel


class Contribution(BaseModel):
    date: MongoDate
    amount_minor: Minor
    transaction_id: PyObjectId | None = None


class Goal(UserScopedModel):
    name: str
    target_amount_minor: Minor
    current_amount_minor: Minor = 0
    target_date: MongoDate | None = None
    priority: str = "medium"  # "high" | "medium" | "low"
    linked_account_id: PyObjectId | None = None
    monthly_reservation_minor: Minor = 0  # FR-10.7 -> feeds Safe-to-Spend
    is_emergency_fund: bool = False  # FR-10.6
    contributions: list[Contribution] = []
    status: str = "active"  # "active" | "achieved" | "archived"
