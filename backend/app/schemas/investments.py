from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from app.models.common import Minor


class InvestmentCreate(BaseModel):
    name: str
    type: str
    invested_minor: Minor
    current_value_minor: Minor
    units: float | None = None
    identifier: str | None = None
    value_as_of: date | None = None
    notes: str | None = None


class InvestmentUpdate(BaseModel):
    name: str | None = None
    invested_minor: Minor | None = None
    current_value_minor: Minor | None = None
    units: float | None = None
    value_as_of: date | None = None
    notes: str | None = None
    archived: bool | None = None
