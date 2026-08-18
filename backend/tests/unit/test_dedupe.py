"""FR-2.11: fingerprinting and idempotent re-upload."""

from __future__ import annotations

from datetime import date

from bson import ObjectId

from app.services.dedupe import assign_fingerprints, compute_fingerprint


def test_same_inputs_produce_same_fingerprint() -> None:
    account_id = ObjectId()
    fp1 = compute_fingerprint(
        account_id=account_id, txn_date=date(2026, 8, 1), amount_minor=-50000,
        merchant_norm="SWIGGY", balance_minor=1000000,
    )
    fp2 = compute_fingerprint(
        account_id=account_id, txn_date=date(2026, 8, 1), amount_minor=-50000,
        merchant_norm="SWIGGY", balance_minor=1000000,
    )
    assert fp1 == fp2


def test_different_account_produces_different_fingerprint() -> None:
    fp1 = compute_fingerprint(
        account_id=ObjectId(), txn_date=date(2026, 8, 1), amount_minor=-50000,
        merchant_norm="SWIGGY", balance_minor=1000000,
    )
    fp2 = compute_fingerprint(
        account_id=ObjectId(), txn_date=date(2026, 8, 1), amount_minor=-50000,
        merchant_norm="SWIGGY", balance_minor=1000000,
    )
    assert fp1 != fp2


def test_assign_fingerprints_dedupes_reimport() -> None:
    account_id = ObjectId()
    rows = [(date(2026, 8, 1), -50000, "SWIGGY", 1000000)]
    fp_run1 = assign_fingerprints(rows, account_id)
    fp_run2 = assign_fingerprints(rows, account_id)
    assert fp_run1 == fp_run2  # re-uploading the same file yields the same fingerprints


def test_same_day_same_amount_repeats_get_distinct_fingerprints_without_balance() -> None:
    account_id = ObjectId()
    # Two ₹200 coffees, same day, no balance column.
    rows = [
        (date(2026, 8, 1), -20000, "COFFEE SHOP", None),
        (date(2026, 8, 1), -20000, "COFFEE SHOP", None),
    ]
    fps = assign_fingerprints(rows, account_id)
    assert fps[0] != fps[1]


def test_same_day_same_amount_with_balance_get_distinct_fingerprints() -> None:
    account_id = ObjectId()
    rows = [
        (date(2026, 8, 1), -20000, "COFFEE SHOP", 980000),
        (date(2026, 8, 1), -20000, "COFFEE SHOP", 960000),
    ]
    fps = assign_fingerprints(rows, account_id)
    assert fps[0] != fps[1]
