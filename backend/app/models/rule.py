from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from app.models.common import Minor, PyObjectId, UserScopedModel


class MatchType(StrEnum):
    EXACT = "exact"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    REGEX = "regex"


class RuleSource(StrEnum):
    USER = "user"
    SEED = "seed"
    LLM_CONFIRMED = "llm_confirmed"


class Rule(UserScopedModel):
    match_type: MatchType
    pattern: str  # normalised merchant form
    direction: str | None = None  # "debit" | "credit" | None
    amount_min_minor: Minor | None = None  # FR-4.10
    amount_max_minor: Minor | None = None
    category_id: PyObjectId
    subcategory_id: PyObjectId | None = None
    kind_override: str | None = None
    priority: int = 100  # higher wins; user rules seed at 1000
    source: RuleSource = RuleSource.USER
    enabled: bool = True
    hit_count: int = 0
    last_hit_at: datetime | None = None
