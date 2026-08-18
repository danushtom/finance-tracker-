from __future__ import annotations

from pydantic import BaseModel

from app.models.common import Minor
from app.models.rule import MatchType


class RuleCreate(BaseModel):
    match_type: MatchType
    pattern: str
    direction: str | None = None
    amount_min_minor: Minor | None = None
    amount_max_minor: Minor | None = None
    category_id: str
    subcategory_id: str | None = None
    kind_override: str | None = None
    priority: int = 1000  # user rules seed at 1000 (section 5.2)
    backfill: bool = False


class RuleUpdate(BaseModel):
    pattern: str | None = None
    direction: str | None = None
    amount_min_minor: Minor | None = None
    amount_max_minor: Minor | None = None
    category_id: str | None = None
    subcategory_id: str | None = None
    priority: int | None = None
    enabled: bool | None = None


class RulePreviewRequest(BaseModel):
    match_type: MatchType
    pattern: str
    direction: str | None = None
    amount_min_minor: Minor | None = None
    amount_max_minor: Minor | None = None


class RulePreviewResponse(BaseModel):
    affected_count: int
    sample: list[str]
