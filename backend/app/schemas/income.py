from __future__ import annotations

from pydantic import BaseModel

from app.models.common import Minor
from app.models.income import IncomeType


class IncomeSourceCreate(BaseModel):
    name: str
    type: IncomeType
    expected_amount_minor: Minor | None = None
    cadence: str = "monthly"
    expected_day_of_month: int | None = None
    match_patterns: list[str] = []


class IncomeSourceUpdate(BaseModel):
    name: str | None = None
    type: IncomeType | None = None
    expected_amount_minor: Minor | None = None
    cadence: str | None = None
    expected_day_of_month: int | None = None
    match_patterns: list[str] | None = None
    active: bool | None = None


class IncomeClassifyRequest(BaseModel):
    source_id: str | None = None
    type: IncomeType | None = None


class IncomeBreakdown(BaseModel):
    month: str
    baseline_received_minor: Minor
    variable_received_minor: Minor
    total_minor: Minor
