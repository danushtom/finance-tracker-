from __future__ import annotations

from app.models.common import Minor, PyObjectId, UserScopedModel


class WishlistItem(UserScopedModel):
    name: str
    price_minor: Minor
    priority: str = "medium"  # "high" | "medium" | "low"
    target_month: str | None = None  # "YYYY-MM"
    url: str | None = None
    note: str | None = None
    status: str = "wanted"  # "wanted" | "purchased" | "dropped"
    purchased_transaction_id: PyObjectId | None = None
    goal_id: PyObjectId | None = None
