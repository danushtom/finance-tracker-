from __future__ import annotations

from app.models.category import CategoryClass
from app.models.common import Minor, MongoDate, PyObjectId, UserScopedModel


class Transaction(UserScopedModel):
    account_id: PyObjectId
    import_id: PyObjectId | None = None

    date: MongoDate

    description_raw: str  # verbatim, never mutated (FR-3.1)
    merchant_norm: str
    merchant_id: PyObjectId | None = None
    counterparty_vpa: str | None = None  # FR-3.4

    amount_minor: Minor  # signed (NFR-5)
    direction: str  # "debit" | "credit"
    balance_minor: Minor | None = None

    kind: str  # "expense" | "income" | "transfer" | "investment" | "refund"
    category_id: PyObjectId | None = None
    subcategory_id: PyObjectId | None = None
    category_class: CategoryClass | None = None  # denormalised for fast aggregation

    income_source_id: PyObjectId | None = None

    confidence: int = 0  # FR-4.3
    categorised_by: str = "none"  # "rule" | "fuzzy" | "llm" | "user" | "none"
    needs_review: bool = False  # FR-4.4

    is_recurring: bool = False
    commitment_id: PyObjectId | None = None

    transfer_pair_id: PyObjectId | None = None  # FR-3.5
    refund_of_id: PyObjectId | None = None  # FR-3.6

    fingerprint: str  # FR-2.11

    tags: list[str] = []
    note: str | None = None
    is_manual: bool = False  # FR-2.15
