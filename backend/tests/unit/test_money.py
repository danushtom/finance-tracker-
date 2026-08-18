"""FR-2.9, FR-2.10, NFR-5."""

from __future__ import annotations

from datetime import date

import pytest

from app.parsers.money import (
    MoneyParseError,
    format_inr_minor,
    parse_statement_date,
    split_minor,
    to_minor,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1,43,000.00", 14_300_000),
        ("1,450.00 Cr", 145_000),
        ("1,450.00 Dr", -145_000),
        ("(2,000.00)", -200_000),
        ("₹500", 50_000),
        ("500", 50_000),
        ("-500", -50_000),
        ("0.01", 1),
        ("1,000", 100_000),
    ],
)
def test_to_minor(raw: str, expected: int) -> None:
    assert to_minor(raw) == expected


def test_to_minor_none_and_blank() -> None:
    assert to_minor(None) is None
    assert to_minor("") is None
    assert to_minor("-") is None


def test_to_minor_invalid_raises() -> None:
    with pytest.raises(MoneyParseError):
        to_minor("12.34.56")


@pytest.mark.parametrize(
    ("minor", "expected"),
    [
        (14_300_000, "₹1,43,000"),
        (100_000, "₹1,000"),
        (50_000, "₹500"),
        (-50_000, "-₹500"),
        (12_345_678_00, "₹1,23,45,678"),
    ],
)
def test_format_inr_minor(minor: int, expected: str) -> None:
    assert format_inr_minor(minor) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("18/08/2026", date(2026, 8, 18)),
        ("18-08-2026", date(2026, 8, 18)),
        ("18-Aug-26", date(2026, 8, 18)),
        ("2026-08-18", date(2026, 8, 18)),
    ],
)
def test_parse_statement_date(raw: str, expected: date) -> None:
    assert parse_statement_date(raw) == expected


def test_split_minor_no_paisa_lost() -> None:
    for amount in [100, 101, 333, 999_999, 1, 3, 7]:
        for weights in [[50, 30, 20], [1, 1, 1], [1, 0, 0], [33, 33, 34]]:
            parts = split_minor(amount, weights)
            assert sum(parts) == amount, (amount, weights, parts)


def test_split_minor_negative_amount() -> None:
    parts = split_minor(-100, [50, 30, 20])
    assert sum(parts) == -100
    assert all(p <= 0 for p in parts)


def test_split_minor_matches_fr84_discretionary_share() -> None:
    # FR-8.4: 50% invest / 30% goals / 20% discretionary of ₹50,000.
    invest, goals, discretionary = split_minor(5_000_000, [50, 30, 20])
    assert discretionary == 1_000_000  # ₹10,000
    assert invest == 2_500_000
    assert goals == 1_500_000
