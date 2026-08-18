"""NFR-10: LLM egress sanitiser — property test: no output ever contains a
4+ digit run, '@', or a currency symbol."""

from __future__ import annotations

import pytest

from app.categorise.sanitiser import UnsafeMerchantError, sanitise_merchant, try_sanitise


@pytest.mark.parametrize("merchant", ["SWIGGY", "CLAUDE AI", "ABC ENTERPRISES", "GOOGLE CLOUD"])
def test_clean_merchants_pass(merchant: str) -> None:
    assert sanitise_merchant(merchant) == merchant


@pytest.mark.parametrize(
    "merchant",
    [
        "SWIGGY 451233098711",  # digit run >= 4
        "swiggyupi@axis",  # VPA fragment
        "₹500 CASHBACK",  # currency symbol
        "$100 REFUND",
        "A" * 100,  # exceeds max length
        "",
    ],
)
def test_unsafe_merchants_rejected(merchant: str) -> None:
    with pytest.raises(UnsafeMerchantError):
        sanitise_merchant(merchant)
    assert try_sanitise(merchant) is None


@pytest.mark.parametrize(
    "merchant",
    [
        "SWIGGY 451233098711",
        "swiggyupi@axis",
        "₹500 CASHBACK",
        "SWIGGY",
        "ABC 123",  # 3-digit run is fine
    ],
)
def test_property_no_unsafe_content_ever_returned(merchant: str) -> None:
    result = try_sanitise(merchant)
    if result is not None:
        assert "@" not in result
        assert "₹" not in result and "$" not in result
        import re

        assert not re.search(r"\d{4,}", result)
