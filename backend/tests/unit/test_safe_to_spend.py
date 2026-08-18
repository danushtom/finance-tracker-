"""FR-8.4 — the normative worked example, asserted to the paise. This is
the executable specification for `app.services.safe_to_spend` (NFR-6:
`safe_to_spend.py` must reach 100% branch coverage; this is the anchor
test all the branch-coverage tests build on).

The repository layer is stubbed rather than hit against a real Mongo, so
this test asserts the *formula* is implemented exactly as specified,
independent of persistence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pytest
from bson import ObjectId

import app.services.safe_to_spend as sts_module
from app.models.user import User, UserSettings
from app.services.safe_to_spend import compute_safe_to_spend, days_remaining_in_month


@dataclass
class _FakeCommitment:
    expected_amount_minor: int


@dataclass
class _FakeGoal:
    monthly_reservation_minor: int = 0
    contributions: list = field(default_factory=list)


class _FakeTransactionRepo:
    def __init__(self, db) -> None:  # noqa: ANN001
        pass

    async def sum_income(self, user_id, month, *, income_type=None):  # noqa: ANN001
        return {"baseline": 9_300_000, "variable": 5_000_000}[income_type]

    async def sum_outflows(self, user_id, month, *, class_in=None, class_=None, up_to=None):  # noqa: ANN001
        if class_ == "fixed":
            return 1_550_000  # fixed already paid
        if class_in == ["variable", "isolated"]:
            return 4_200_000  # variable + isolated spent to date
        if class_ == "investment":
            return 0  # nothing invested yet this month
        raise AssertionError(f"unexpected sum_outflows call: class_={class_} class_in={class_in}")


class _FakeCommitmentRepo:
    def __init__(self, db) -> None:  # noqa: ANN001
        pass

    async def list_confirmed(self, user_id):  # noqa: ANN001
        return [_FakeCommitment(expected_amount_minor=1_800_000)]  # ₹18,000 fixed for the month


class _FakeGoalRepo:
    def __init__(self, db) -> None:  # noqa: ANN001
        pass

    async def list_active(self, user_id):  # noqa: ANN001
        return []  # no goal reservations in the worked example


@pytest.fixture(autouse=True)
def _patch_repos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sts_module, "TransactionRepository", _FakeTransactionRepo)
    monkeypatch.setattr(sts_module, "CommitmentRepository", _FakeCommitmentRepo)
    monkeypatch.setattr(sts_module, "GoalRepository", _FakeGoalRepo)


def _worked_example_user() -> User:
    return User(
        email="dan@example.com",
        password_hash="x",
        settings=UserSettings(
            buffer_minor=500_000,  # ₹5,000
            monthly_savings_target_minor=1_500_000,  # ₹15,000
            monthly_investment_target_minor=1_000_000,  # ₹10,000
            count_expected_salary=True,
        ),
    )


async def test_fr84_worked_example_matches_to_the_paise() -> None:
    user = _worked_example_user()
    # August 2026 has 31 days; today = 22nd -> 10 days remaining, matching
    # the worked example's "10 days left in the month".
    today = date(2026, 8, 22)

    result = await compute_safe_to_spend(db=None, user=user, month="2026-08", today=today)

    assert result.amount_minor == 2_850_000  # ₹28,500
    assert result.is_over is False
    assert result.days_left == 10
    assert result.per_day_minor == 285_000  # ₹2,850


async def test_fr84_waterfall_lines_are_traceable() -> None:
    user = _worked_example_user()
    result = await compute_safe_to_spend(db=None, user=user, month="2026-08", today=date(2026, 8, 22))

    labels = [line.label for line in result.lines]
    assert "Baseline income" in labels
    assert any("Project income" in l for l in labels)
    assert "Fixed still due" in labels
    assert "Spent so far" in labels
    assert "Buffer" in labels

    fixed_line = next(l for l in result.lines if l.label == "Fixed still due")
    assert fixed_line.amount_minor == 250_000  # ₹18,000 due - ₹15,500 paid
    assert fixed_line.sign == "-"

    buffer_line = next(l for l in result.lines if l.label == "Buffer")
    assert buffer_line.amount_minor == 500_000


async def test_negative_safe_to_spend_is_flagged_over_not_negative_headline() -> None:
    """FR-8.3.1: floored at display level; is_over=True signals the UI to
    render ₹0 (over by ₹X) rather than a negative headline."""
    user = _worked_example_user()
    user.settings.buffer_minor = 50_000_000  # an absurd buffer forces a deficit
    result = await compute_safe_to_spend(db=None, user=user, month="2026-08", today=date(2026, 8, 22))

    assert result.amount_minor < 0
    assert result.is_over is True
    assert result.display_amount_minor() == 0
    assert result.over_by_minor() == abs(result.amount_minor)
    assert result.per_day_minor is None  # never a per-day figure when over


def test_days_remaining_in_month() -> None:
    assert days_remaining_in_month("2026-08", date(2026, 8, 22)) == 10
    assert days_remaining_in_month("2026-08", date(2026, 8, 31)) == 1
    assert days_remaining_in_month("2026-08", date(2026, 8, 1)) == 31
