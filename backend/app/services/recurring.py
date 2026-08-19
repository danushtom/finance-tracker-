"""Recurring-transaction detection (FR-7.1, section 8.4).

For each `merchant_norm` with >=2 debits in the last 12 months: sort dates,
compute deltas, and if the median delta falls within a cadence window
(28-31 / 7 / 88-92 / 360-370 days) with low variance, and amounts are
within +/-15% of their median, emit a **candidate** commitment with
`status = "detected"`. Candidates require user confirmation before being
counted as committed (FR-7.2) — this module never sets `status=confirmed`.
"""

from __future__ import annotations

import statistics
from datetime import date, timedelta

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.commitment import Commitment, CommitmentStatus
from app.models.common import to_utc_datetime
from app.repositories.commitments import CommitmentRepository
from app.repositories.transactions import TransactionRepository

_CADENCE_WINDOWS: dict[str, tuple[int, int]] = {
    "weekly": (6, 8),
    "monthly": (28, 31),
    "quarterly": (88, 92),
    "yearly": (360, 370),
}
_AMOUNT_TOLERANCE = 0.15
_MIN_OCCURRENCES = 2


def _classify_cadence(median_delta_days: float) -> str | None:
    for cadence, (low, high) in _CADENCE_WINDOWS.items():
        if low <= median_delta_days <= high:
            return cadence
    return None


def _amounts_consistent(amounts: list[int]) -> bool:
    median = statistics.median(amounts)
    if median == 0:
        return False
    return all(abs(a - median) <= abs(median) * _AMOUNT_TOLERANCE for a in amounts)


async def detect_recurring_commitments(db: AsyncIOMotorDatabase, user_id: ObjectId) -> list[Commitment]:
    txn_repo = TransactionRepository(db)
    commitment_repo = CommitmentRepository(db)

    # `to_utc_datetime`: BSON cannot encode a bare `date` in a query filter.
    cutoff = to_utc_datetime(date.today() - timedelta(days=365))
    debits = await txn_repo.find(
        user_id, {"direction": "debit", "date": {"$gte": cutoff}}, sort=[("date", 1)]
    )

    by_merchant: dict[str, list] = {}
    for txn in debits:
        by_merchant.setdefault(txn.merchant_norm, []).append(txn)

    candidates: list[Commitment] = []
    for merchant_norm, txns in by_merchant.items():
        if len(txns) < _MIN_OCCURRENCES:
            continue
        dates = sorted(t.date for t in txns)
        deltas = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
        if not deltas:
            continue
        median_delta = statistics.median(deltas)
        cadence = _classify_cadence(median_delta)
        if cadence is None:
            continue

        amounts = [abs(t.amount_minor) for t in txns]
        if not _amounts_consistent(amounts):
            continue

        existing = await commitment_repo.find_by_merchant(user_id, merchant_norm)
        if existing is not None and existing.status != CommitmentStatus.DETECTED:
            continue  # already confirmed or cancelled; don't re-surface

        expected_amount = int(statistics.median(amounts))
        last_txn = txns[-1]
        next_expected = _next_expected_date(last_txn.date, cadence)

        if existing is not None:
            await commitment_repo.update(
                user_id,
                existing.id,
                {
                    "$set": {
                        "expected_amount_minor": expected_amount,
                        "cadence": cadence,
                        "next_expected_date": next_expected,
                    }
                },
            )
            continue

        commitment = Commitment(
            user_id=user_id,
            merchant_norm=merchant_norm,
            display_name=merchant_norm,
            category_id=last_txn.category_id,
            expected_amount_minor=expected_amount,
            cadence=cadence,
            next_expected_date=next_expected,
            status=CommitmentStatus.DETECTED,
        )
        await commitment_repo.insert(commitment)
        candidates.append(commitment)

    return candidates


def _next_expected_date(last_date: date, cadence: str) -> date:
    days = {"weekly": 7, "monthly": 30, "quarterly": 90, "yearly": 365}[cadence]
    return last_date + timedelta(days=days)
