"""FR-9.2, FR-9.4: affordability verdicts and months-to-afford."""

from __future__ import annotations

from bson import ObjectId

from app.models.wishlist import WishlistItem
from app.services.affordability import evaluate_item
from app.services.safe_to_spend import SafeToSpend


def _sts(amount_minor: int) -> SafeToSpend:
    return SafeToSpend(
        month="2026-08", amount_minor=amount_minor, is_over=amount_minor < 0,
        per_day_minor=None, days_left=10, lines=[],
    )


def _item(price_minor: int) -> WishlistItem:
    return WishlistItem(user_id=ObjectId(), name="NVMe SSD", price_minor=price_minor)


def test_affordable_item_shows_remaining_after_purchase() -> None:
    verdict = evaluate_item(_item(500_000), _sts(2_850_000), surplus_minor=1_000_000)
    assert verdict.affordable is True
    assert verdict.shortfall_minor == 0
    assert verdict.remaining_after_purchase_minor == 2_350_000
    assert verdict.months_to_afford is None


def test_unaffordable_item_computes_months_to_afford() -> None:
    # price ₹35,650, available ₹28,500 -> shortfall ₹7,150; surplus ₹2,000/mo
    verdict = evaluate_item(_item(3_565_000), _sts(2_850_000), surplus_minor=200_000)
    assert verdict.affordable is False
    assert verdict.shortfall_minor == 715_000
    assert verdict.remaining_after_purchase_minor is None
    # ceil(715_000 / 200_000) = 4
    assert verdict.months_to_afford == 4


def test_unaffordable_with_no_surplus_reports_not_on_cash_flow() -> None:
    """FR-9.4: if projected surplus <= 0, no misleading months-to-afford
    number — "not on current cash flow" instead."""
    verdict = evaluate_item(_item(1_000_000), _sts(0), surplus_minor=0)
    assert verdict.affordable is False
    assert verdict.months_to_afford is None
    assert verdict.on_current_cash_flow is False


def test_negative_safe_to_spend_treated_as_zero_available() -> None:
    verdict = evaluate_item(_item(100_000), _sts(-50_000), surplus_minor=500_000)
    assert verdict.affordable is False
    assert verdict.shortfall_minor == 100_000  # available floors at 0, not -50,000
