"""Idempotent re-upload via fingerprinting (FR-2.11, section 7.5).

Uniqueness is enforced by the DB's unique `{user_id, fingerprint}` index —
correctness does not depend on an application-level check winning a race
(ADR-8). This module only computes the fingerprint; `insert_many_dedup` in
`app.repositories.transactions` does the insert and counts `E11000`s.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import date

from bson import ObjectId


def compute_fingerprint(
    *,
    account_id: ObjectId,
    txn_date: date,
    amount_minor: int,
    merchant_norm: str,
    balance_minor: int | None,
    occurrence_index: int = 0,
) -> str:
    balance_part = str(balance_minor) if balance_minor is not None else ""
    raw = f"{account_id}|{txn_date:%Y-%m-%d}|{amount_minor}|{merchant_norm}|{balance_part}"
    if balance_minor is None and occurrence_index:
        raw += f"|{occurrence_index}"
    return hashlib.sha256(raw.encode()).hexdigest()


def assign_fingerprints(
    rows: list[tuple[date, int, str, int | None]], account_id: ObjectId
) -> list[str]:
    """Handles genuine same-day same-amount repeats (two ₹200 coffees) that
    lack a distinguishing `balance_minor`: within a single file, a
    monotonic `occurrence_index` is appended for identical keys."""
    seen_counts: dict[tuple, int] = defaultdict(int)
    fingerprints: list[str] = []
    for txn_date, amount_minor, merchant_norm, balance_minor in rows:
        key = (txn_date, amount_minor, merchant_norm, balance_minor)
        occurrence_index = seen_counts[key]
        seen_counts[key] += 1
        fingerprints.append(
            compute_fingerprint(
                account_id=account_id,
                txn_date=txn_date,
                amount_minor=amount_minor,
                merchant_norm=merchant_norm,
                balance_minor=balance_minor,
                occurrence_index=occurrence_index if balance_minor is None else 0,
            )
        )
    return fingerprints
