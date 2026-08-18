"""FR-4.1, FR-4.10: rule matching precedence and amount-conditional rules."""

from __future__ import annotations

from bson import ObjectId

from app.categorise.rules import RuleSet
from app.models.rule import MatchType, Rule, RuleSource


def _rule(**kwargs) -> Rule:  # noqa: ANN003
    defaults = dict(
        user_id=ObjectId(),
        match_type=MatchType.CONTAINS,
        pattern="SWIGGY",
        category_id=ObjectId(),
        priority=100,
        source=RuleSource.USER,
    )
    defaults.update(kwargs)
    return Rule(**defaults)


def test_exact_match() -> None:
    rule = _rule(match_type=MatchType.EXACT, pattern="SWIGGY")
    rule_set = RuleSet([rule])
    assert rule_set.match("SWIGGY") is rule
    assert rule_set.match("SWIGGY BANGALORE") is None


def test_contains_match() -> None:
    rule = _rule(match_type=MatchType.CONTAINS, pattern="SWIGGY")
    rule_set = RuleSet([rule])
    assert rule_set.match("SWIGGY BANGALORE") is rule


def test_starts_with_match() -> None:
    rule = _rule(match_type=MatchType.STARTS_WITH, pattern="AMAZON")
    rule_set = RuleSet([rule])
    assert rule_set.match("AMAZON RETAIL") is rule
    assert rule_set.match("MY AMAZON") is None


def test_regex_match() -> None:
    rule = _rule(match_type=MatchType.REGEX, pattern=r"^UBER.*TRIP$")
    rule_set = RuleSet([rule])
    assert rule_set.match("UBER INDIA TRIP") is rule


def test_higher_priority_wins_among_pattern_rules() -> None:
    low = _rule(pattern="AMAZON", priority=100)
    high = _rule(pattern="AMAZON", priority=1000)
    rule_set = RuleSet([low, high])
    assert rule_set.match("AMAZON RETAIL") is high


def test_amount_conditional_rule_respects_bounds() -> None:
    rule = _rule(pattern="AMAZON", amount_min_minor=500_000)  # >= ₹5,000
    rule_set = RuleSet([rule])
    assert rule_set.match("AMAZON RETAIL", amount_minor=600_000) is rule
    assert rule_set.match("AMAZON RETAIL", amount_minor=100_000) is None


def test_direction_condition() -> None:
    rule = _rule(pattern="SALARY", direction="credit")
    rule_set = RuleSet([rule])
    assert rule_set.match("SALARY ACME", direction="credit") is rule
    assert rule_set.match("SALARY ACME", direction="debit") is None
