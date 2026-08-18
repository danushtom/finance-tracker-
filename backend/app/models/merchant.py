from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from app.models.common import Minor, PyObjectId, UserScopedModel


class MerchantSource(StrEnum):
    USER = "user"
    LLM = "llm"
    SEED = "seed"


class Merchant(UserScopedModel):
    merchant_norm: str
    display_name: str
    category_id: PyObjectId | None = None
    subcategory_id: PyObjectId | None = None
    confidence: int = 0
    source: MerchantSource = MerchantSource.SEED
    txn_count: int = 0
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    total_minor: Minor = 0
