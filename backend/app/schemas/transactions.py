from __future__ import annotations

# Aliased: TransactionCreate.date would otherwise shadow this type name
# during pydantic's `from __future__ import annotations` evaluation.
from datetime import date as _date

from pydantic import BaseModel

from app.models.common import Minor


class TransactionCreate(BaseModel):
    account_id: str
    date: _date
    description_raw: str
    amount_minor: Minor
    direction: str
    kind: str = "expense"
    category_id: str | None = None
    note: str | None = None


class TransactionUpdate(BaseModel):
    category_id: str | None = None
    subcategory_id: str | None = None
    kind: str | None = None
    note: str | None = None
    tags: list[str] | None = None


class RuleSuggestion(BaseModel):
    match_type: str
    pattern: str
    affected_past_count: int
    affected_future: bool = True


class TransactionUpdateResponse(BaseModel):
    id: str
    rule_suggestion: RuleSuggestion | None = None


class BulkCategoriseRequest(BaseModel):
    transaction_ids: list[str]
    category_id: str


class SplitLine(BaseModel):
    category_id: str
    amount_minor: Minor
    note: str | None = None


class SplitRequest(BaseModel):
    lines: list[SplitLine]
