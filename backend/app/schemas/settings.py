from __future__ import annotations

from pydantic import BaseModel

from app.models.common import Minor
from app.models.user import LLMSettings, VariableSplit


class SettingsUpdate(BaseModel):
    currency: str | None = None
    buffer_minor: Minor | None = None
    low_confidence_threshold: int | None = None
    monthly_savings_target_minor: Minor | None = None
    monthly_investment_target_minor: Minor | None = None
    variable_split: VariableSplit | None = None
    count_expected_salary: bool | None = None
    llm: LLMSettings | None = None
    month_start_day: int | None = None
