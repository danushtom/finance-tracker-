from __future__ import annotations

from pydantic import BaseModel

from app.models.common import Minor, PyObjectId, UserScopedModel


class NetWorthBreakdownEntry(BaseModel):
    account_id: PyObjectId
    type: str
    value_minor: Minor


class NetWorthSnapshot(UserScopedModel):
    month: str  # "YYYY-MM"
    assets_minor: Minor
    liabilities_minor: Minor
    net_worth_minor: Minor
    breakdown: list[NetWorthBreakdownEntry] = []
