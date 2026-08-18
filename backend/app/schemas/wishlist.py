from __future__ import annotations

from pydantic import BaseModel

from app.models.common import Minor


class WishlistItemCreate(BaseModel):
    name: str
    price_minor: Minor
    priority: str = "medium"
    target_month: str | None = None
    url: str | None = None
    note: str | None = None


class WishlistItemUpdate(BaseModel):
    name: str | None = None
    price_minor: Minor | None = None
    priority: str | None = None
    target_month: str | None = None
    url: str | None = None
    note: str | None = None
    status: str | None = None


class WishlistVerdict(BaseModel):
    item_id: str
    name: str
    price_minor: Minor
    priority: str
    affordable: bool
    remaining_after_purchase_minor: Minor | None
    shortfall_minor: Minor
    months_to_afford: int | None
    on_current_cash_flow: bool


class SimulateRequest(BaseModel):
    item_ids: list[str]


class SimulateResponse(BaseModel):
    items: list[WishlistVerdict]
    combined_affordable: bool
    combined_total_minor: Minor
    remaining_after_all_minor: Minor | None
