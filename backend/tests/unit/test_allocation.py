"""FR-12: variable-income allocation split maths."""

from __future__ import annotations

from app.models.user import VariableSplit
from app.parsers.money import split_minor
from app.services.allocation import projected_value


def test_default_split_sums_exactly() -> None:
    split = VariableSplit()  # 50 / 30 / 20
    parts = split_minor(5_000_000, [split.invest_pct, split.goals_pct, split.discretionary_pct])
    assert sum(parts) == 5_000_000
    assert parts == [2_500_000, 1_500_000, 1_000_000]


def test_projected_value_states_assumption_explicitly() -> None:
    # ₹50,000 at 10% for 10 years ~= ₹129,687
    value = projected_value(5_000_000, years=10, annual_rate_pct=10)
    assert value == int(5_000_000 * (1.10**10))
