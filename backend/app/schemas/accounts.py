from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from app.models.account import AccountType
from app.models.common import Minor


class AccountCreate(BaseModel):
    name: str
    type: AccountType
    institution: str | None = None
    last4: str | None = None
    current_balance_minor: Minor = 0
    balance_as_of: date | None = None


class AccountUpdate(BaseModel):
    name: str | None = None
    institution: str | None = None
    last4: str | None = None
    current_balance_minor: Minor | None = None
    balance_as_of: date | None = None
    archived: bool | None = None
    column_mapping: dict | None = None
