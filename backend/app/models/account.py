from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import model_validator

from app.models.common import Minor, MongoDate, UserScopedModel


class AccountType(StrEnum):
    BANK = "bank"
    CASH = "cash"
    CREDIT_CARD = "credit_card"
    BROKERAGE = "brokerage"
    MF_FOLIO = "mf_folio"
    PPF_EPF = "ppf_epf"
    ASSET = "asset"
    LIABILITY = "liability"


_LIABILITY_TYPES = {AccountType.CREDIT_CARD, AccountType.LIABILITY}


class Account(UserScopedModel):
    name: str
    type: AccountType
    institution: str | None = None
    last4: str | None = None
    current_balance_minor: Minor = 0
    balance_as_of: MongoDate | None = None
    is_asset: bool = True
    column_mapping: dict[str, Any] | None = None  # FR-2.6
    archived: bool = False

    @model_validator(mode="before")
    @classmethod
    def _default_is_asset(cls, data: Any) -> Any:
        if isinstance(data, dict) and "is_asset" not in data and "type" in data:
            data["is_asset"] = AccountType(data["type"]) not in _LIABILITY_TYPES
        return data
