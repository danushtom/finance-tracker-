from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, ValidationInfo, field_validator

from app.models.common import Minor, MongoModel


class VariableSplit(BaseModel):
    """Must sum to 100 — validated here, not only in the UI (FR-12.1)."""

    invest_pct: int = 50
    goals_pct: int = 30
    discretionary_pct: int = 20

    @field_validator("discretionary_pct")
    @classmethod
    def _sums_to_100(cls, v: int, info: ValidationInfo) -> int:
        total = info.data.get("invest_pct", 0) + info.data.get("goals_pct", 0) + v
        if total != 100:
            raise ValueError(f"variable_split percentages must sum to 100, got {total}")
        return v


class LLMSettings(BaseModel):
    """Per-user LLM configuration (FR-4.2, FR-4.12, FR-4.13, NFR-11).

    The user chooses which provider categorises their unknown merchants and
    supplies their own key for it. `provider = "none"` (or an empty key)
    degrades categorisation to rules-only; the app stays fully usable
    either way.
    """

    provider: str = "gemini"  # "gemini" | "claude" | "none"
    gemini_api_key: str | None = None
    claude_api_key: str | None = None
    monthly_call_cap: int = 500

    @field_validator("provider")
    @classmethod
    def _valid_provider(cls, v: str) -> str:
        if v not in {"gemini", "claude", "none"}:
            raise ValueError("provider must be one of: gemini, claude, none")
        return v


class UserSettings(BaseModel):
    currency: str = "INR"
    timezone: str = "Asia/Kolkata"
    month_start_day: int = 1  # Q-2 hook
    buffer_minor: Minor = 500_000  # ₹5,000 (FR-8.3)
    low_confidence_threshold: int = 70  # FR-4.4
    monthly_savings_target_minor: Minor = 0
    monthly_investment_target_minor: Minor = 0
    variable_split: VariableSplit = Field(default_factory=VariableSplit)
    count_expected_salary: bool = True  # FR-8.3.4
    llm: LLMSettings = Field(default_factory=LLMSettings)


class User(MongoModel):
    email: EmailStr
    password_hash: str
    display_name: str = ""
    settings: UserSettings = Field(default_factory=UserSettings)
    llm_calls_this_month: int = 0
    llm_calls_month: str = ""  # "YYYY-MM"
    data_version: int = 0  # bumped on every mutating write (FR-8.3.6)
