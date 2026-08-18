"""Income source matching (FR-6.2)."""

from __future__ import annotations

from app.models.income import IncomeSource


def match_income_source(merchant_norm: str, sources: list[IncomeSource]) -> IncomeSource | None:
    for source in sources:
        if not source.active:
            continue
        for pattern in source.match_patterns:
            if pattern.upper() in merchant_norm:
                return source
    return None
