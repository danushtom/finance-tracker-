from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from app.models.common import Minor, MongoDate, PyObjectId, UserScopedModel


class CommitmentStatus(StrEnum):
    DETECTED = "detected"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class AmountHistoryEntry(BaseModel):
    date: MongoDate
    amount_minor: Minor


class Commitment(UserScopedModel):
    merchant_norm: str
    display_name: str
    category_id: PyObjectId | None = None
    expected_amount_minor: Minor
    cadence: str  # "monthly" | "weekly" | "quarterly" | "yearly"
    day_of_month: int | None = None
    next_expected_date: MongoDate | None = None
    status: CommitmentStatus = CommitmentStatus.DETECTED
    amount_history: list[AmountHistoryEntry] = []
