"""FR-3.1: merchant normalisation fixture corpus."""

from __future__ import annotations

import pytest

from app.services.normalise import normalise_merchant


@pytest.mark.parametrize(
    ("raw", "expected_merchant"),
    [
        ("UPI/DR/451233098711/SWIGGY/HDFC/swiggyupi@axis/Payment from Ph", "SWIGGY HDFC"),
        ("UPI/CR/402198765432/ZOMATO ONLINE/YESB/zomato@ybl", "ZOMATO ONLINE YESB"),
        ("NEFT/N012345678901/ACME PVT LTD/SALARY", "ACME PVT LTD SALARY"),
        ("POS 12345678 AMAZON RETAIL 18/08/26", "AMAZON RETAIL"),
        ("ATM WDL 998877 NEW DELHI", "ATM WDL NEW DELHI"),
        ("IMPS/123456789012/JOHN DOE/HDFC0001234", "JOHN DOE HDFC"),
    ],
)
def test_normalise_merchant(raw: str, expected_merchant: str) -> None:
    result = normalise_merchant(raw)
    assert result.merchant_norm == expected_merchant


def test_extract_vpa() -> None:
    result = normalise_merchant("UPI/DR/451233098711/SWIGGY/HDFC/swiggyupi@axis/Payment from Ph")
    assert result.counterparty_vpa == "swiggyupi@axis"


def test_no_vpa_present() -> None:
    result = normalise_merchant("NEFT/N012345678901/ACME PVT LTD/SALARY")
    assert result.counterparty_vpa is None


def test_empty_description_falls_back_to_unknown() -> None:
    result = normalise_merchant("123456 18/08/2026")
    assert result.merchant_norm == "UNKNOWN"


def test_normalisation_is_deterministic() -> None:
    raw = "UPI/DR/451233098711/SWIGGY/HDFC/swiggyupi@axis/Payment from Ph"
    assert normalise_merchant(raw).merchant_norm == normalise_merchant(raw).merchant_norm
