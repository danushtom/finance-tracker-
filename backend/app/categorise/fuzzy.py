"""Fuzzy match against previously categorised merchants (FR-4.1 stage 6).

`token_set_ratio` >= 88 is treated as a hit, confidence capped at 88
regardless of the raw score (section 8.1 pipeline table).
"""

from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz, process

from app.models.merchant import Merchant

FUZZY_THRESHOLD = 88
CONFIDENCE_CAP = 88


@dataclass
class FuzzyMatch:
    merchant: Merchant
    score: float
    confidence: int


def find_best_match(merchant_norm: str, known: list[Merchant]) -> FuzzyMatch | None:
    if not known:
        return None
    choices = {i: m.merchant_norm for i, m in enumerate(known)}
    result = process.extractOne(merchant_norm, choices, scorer=fuzz.token_set_ratio)
    if result is None:
        return None
    _, score, idx = result
    if score < FUZZY_THRESHOLD:
        return None
    return FuzzyMatch(merchant=known[idx], score=score, confidence=min(CONFIDENCE_CAP, round(score)))
