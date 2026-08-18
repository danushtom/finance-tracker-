from __future__ import annotations

from pydantic import BaseModel

from app.models.common import Minor


class AllocationCreate(BaseModel):
    transaction_id: str


class AllocationOverride(BaseModel):
    invest_minor: Minor
    goals_minor: Minor
    discretionary_minor: Minor
