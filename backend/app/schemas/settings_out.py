"""Output-only settings shapes that mask secrets before they ever leave the
API (NFR-8: "No secret is ever committed, logged, or returned by an API" —
applies even to a user's own key, so a GET never echoes it back verbatim)."""

from __future__ import annotations

from pydantic import BaseModel

from app.models.common import Minor
from app.models.user import LLMSettings, UserSettings, VariableSplit


def _mask(key: str | None) -> str | None:
    if not key:
        return None
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:4]}...{key[-4:]}"


class LLMSettingsOut(BaseModel):
    provider: str
    monthly_call_cap: int
    gemini_api_key_set: bool
    gemini_api_key_masked: str | None
    claude_api_key_set: bool
    claude_api_key_masked: str | None

    @classmethod
    def from_model(cls, llm: LLMSettings) -> "LLMSettingsOut":
        return cls(
            provider=llm.provider,
            monthly_call_cap=llm.monthly_call_cap,
            gemini_api_key_set=bool(llm.gemini_api_key),
            gemini_api_key_masked=_mask(llm.gemini_api_key),
            claude_api_key_set=bool(llm.claude_api_key),
            claude_api_key_masked=_mask(llm.claude_api_key),
        )


class UserSettingsOut(BaseModel):
    currency: str
    timezone: str
    month_start_day: int
    buffer_minor: Minor
    low_confidence_threshold: int
    monthly_savings_target_minor: Minor
    monthly_investment_target_minor: Minor
    variable_split: VariableSplit
    count_expected_salary: bool
    llm: LLMSettingsOut

    @classmethod
    def from_model(cls, settings: UserSettings) -> "UserSettingsOut":
        return cls(
            currency=settings.currency,
            timezone=settings.timezone,
            month_start_day=settings.month_start_day,
            buffer_minor=settings.buffer_minor,
            low_confidence_threshold=settings.low_confidence_threshold,
            monthly_savings_target_minor=settings.monthly_savings_target_minor,
            monthly_investment_target_minor=settings.monthly_investment_target_minor,
            variable_split=settings.variable_split,
            count_expected_salary=settings.count_expected_salary,
            llm=LLMSettingsOut.from_model(settings.llm),
        )
