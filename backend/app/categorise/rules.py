"""In-memory rule set and matching (FR-4.1 stages 1/3, FR-4.10, section 8.1).

Rules are loaded once per import into a `RuleSet` — exact rules in a dict,
pattern rules in a priority-sorted list — so there is no per-transaction DB
round-trip even for a few hundred rules (section 8.1).

User regexes are length-capped and matched under a timeout to avoid
catastrophic backtracking (section 13 Security table) — a single shared
worker thread enforces the timeout without spawning a thread per match.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass

from app.models.rule import MatchType, Rule

MAX_PATTERN_LENGTH = 200
REGEX_TIMEOUT_S = 0.1

_regex_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="rule-regex")


class UnsafeRulePatternError(ValueError):
    pass


def validate_pattern(match_type: MatchType, pattern: str) -> None:
    if len(pattern) > MAX_PATTERN_LENGTH:
        raise UnsafeRulePatternError(f"Pattern exceeds max length of {MAX_PATTERN_LENGTH}")
    if match_type == MatchType.REGEX:
        try:
            re.compile(pattern)
        except re.error as exc:
            raise UnsafeRulePatternError(f"Invalid regex: {exc}") from exc


def _regex_match(compiled: re.Pattern, text: str) -> bool:
    future = _regex_executor.submit(lambda: compiled.search(text) is not None)
    try:
        return future.result(timeout=REGEX_TIMEOUT_S)
    except FutureTimeoutError:
        future.cancel()
        return False


@dataclass
class MatchResult:
    rule: Rule


class RuleSet:
    """Loaded once per import (or per categorisation request) from
    `RuleRepository.list_enabled`."""

    def __init__(self, rules: list[Rule]) -> None:
        self._exact: dict[str, Rule] = {}
        self._patterns: list[tuple[Rule, re.Pattern | None]] = []
        for rule in sorted(rules, key=lambda r: r.priority, reverse=True):
            if rule.match_type == MatchType.EXACT:
                self._exact.setdefault(rule.pattern, rule)
            else:
                compiled = re.compile(rule.pattern, re.IGNORECASE) if rule.match_type == MatchType.REGEX else None
                self._patterns.append((rule, compiled))

    def match(
        self, merchant_norm: str, *, direction: str | None = None, amount_minor: int | None = None
    ) -> Rule | None:
        exact = self._exact.get(merchant_norm)
        if exact and _passes_conditions(exact, direction, amount_minor):
            return exact

        for rule, compiled in self._patterns:
            if not _passes_conditions(rule, direction, amount_minor):
                continue
            if rule.match_type == MatchType.CONTAINS and rule.pattern.upper() in merchant_norm:
                return rule
            if rule.match_type == MatchType.STARTS_WITH and merchant_norm.startswith(rule.pattern.upper()):
                return rule
            if rule.match_type == MatchType.REGEX and compiled is not None:
                if _regex_match(compiled, merchant_norm):
                    return rule
        return None

    def match_by_source(self, merchant_norm: str, sources: set[str]) -> Rule | None:
        rule = self.match(merchant_norm)
        if rule and rule.source.value in sources:
            return rule
        return None


def _passes_conditions(rule: Rule, direction: str | None, amount_minor: int | None) -> bool:
    if rule.direction and direction and rule.direction != direction:
        return False
    if amount_minor is not None:
        abs_amount = abs(amount_minor)
        if rule.amount_min_minor is not None and abs_amount < rule.amount_min_minor:
            return False
        if rule.amount_max_minor is not None and abs_amount > rule.amount_max_minor:
            return False
    return True
