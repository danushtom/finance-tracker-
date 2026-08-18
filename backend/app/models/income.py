from __future__ import annotations

from enum import StrEnum

from app.models.common import Minor, UserScopedModel


class IncomeType(StrEnum):
    BASELINE = "baseline"
    VARIABLE = "variable"


class IncomeSource(UserScopedModel):
    name: str
    type: IncomeType
    expected_amount_minor: Minor | None = None
    cadence: str = "monthly"  # "monthly" | "irregular"
    expected_day_of_month: int | None = None
    match_patterns: list[str] = []
    active: bool = True
