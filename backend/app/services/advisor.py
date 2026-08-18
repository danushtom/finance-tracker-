"""Monthly plain-language summary and anomaly notices (FR-11).

Every figure is derived from the user's actual transaction history; the
sentence is a **template with computed values substituted** — there is no
LLM anywhere in this module (FR-11.2). Requires >=2 complete months of
history, else returns `insufficient_data` with what is known (FR-11.4).
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.common import Minor
from app.models.user import User
from app.parsers.money import format_inr_minor
from app.repositories.commitments import CommitmentRepository
from app.repositories.transactions import TransactionRepository
from app.services.date_utils import last_n_months

MIN_MONTHS_OF_DATA = 2


def floor_to_500(amount: Minor) -> Minor:
    step = 50_000  # ₹500 in paise
    return max(0, (amount // step) * step)


@dataclass
class AdvisorSummary:
    has_enough_data: bool
    months_of_data: int
    baseline_income_minor: Minor
    median_fixed_minor: Minor
    median_variable_minor: Minor
    recommended_allocation_minor: Minor
    sentence: str


@dataclass
class Anomaly:
    kind: str
    message: str
    severity: str  # "info" | "warning"


async def _months_with_data(db: AsyncIOMotorDatabase, user_id: ObjectId) -> int:
    """Counts distinct months (of the last 12) that have at least one
    transaction, so FR-11.4's "2 complete months" gate isn't fooled by a
    single statement spanning several calendar months with sparse data."""
    txn_repo = TransactionRepository(db)
    months = last_n_months(date.today(), 12)
    distinct_months = 0
    for m in months:
        has_spend = await txn_repo.sum_outflows(user_id, m, class_in=["fixed", "variable", "isolated"])
        has_income = await txn_repo.sum_income(user_id, m)
        if has_spend or has_income:
            distinct_months += 1
    return distinct_months


async def build_summary(db: AsyncIOMotorDatabase, user: User, *, today: date | None = None) -> AdvisorSummary:
    today = today or date.today()
    txn_repo = TransactionRepository(db)
    months = last_n_months(today, 3)

    months_of_data = await _months_with_data(db, user.id)
    if months_of_data < MIN_MONTHS_OF_DATA:
        return AdvisorSummary(
            has_enough_data=False,
            months_of_data=months_of_data,
            baseline_income_minor=0,
            median_fixed_minor=0,
            median_variable_minor=0,
            recommended_allocation_minor=0,
            sentence=(
                f"We don't have enough history yet ({months_of_data} month"
                f"{'s' if months_of_data != 1 else ''} of data, {MIN_MONTHS_OF_DATA} needed). "
                "Import more statements to unlock a personalised summary."
            ),
        )

    baselines = [await txn_repo.sum_income(user.id, m, income_type="baseline") for m in months]
    fixed = [await txn_repo.sum_outflows(user.id, m, class_="fixed") for m in months]
    variable = [await txn_repo.sum_outflows(user.id, m, class_in=["variable", "isolated"]) for m in months]

    baseline_income = int(statistics.median(baselines))
    median_fixed = int(statistics.median(fixed))
    median_variable = int(statistics.median(variable))

    # FR-11.3
    recommended = floor_to_500(max(0, baseline_income - median_fixed - median_variable - user.settings.buffer_minor))

    sentence = (
        f"Your baseline income is {format_inr_minor(baseline_income)}. "
        f"Your recurring commitments are {format_inr_minor(median_fixed)}. "
        f"Your median discretionary spend over the last 3 months is {format_inr_minor(median_variable)}. "
        f"You can comfortably allocate about {format_inr_minor(recommended)}/month to savings and investing."
    )

    return AdvisorSummary(
        has_enough_data=True,
        months_of_data=months_of_data,
        baseline_income_minor=baseline_income,
        median_fixed_minor=median_fixed,
        median_variable_minor=median_variable,
        recommended_allocation_minor=recommended,
        sentence=sentence,
    )


async def detect_anomalies(db: AsyncIOMotorDatabase, user: User, *, today: date | None = None) -> list[Anomaly]:
    """FR-11.6: category >150% of 3-month median, a new recurring charge, a
    commitment price increase, an unusually large single transaction."""
    today = today or date.today()
    txn_repo = TransactionRepository(db)
    commitment_repo = CommitmentRepository(db)
    current_month = f"{today:%Y-%m}"
    prior_months = _last_n_months(today, 4)[1:]  # exclude current month

    anomalies: list[Anomaly] = []

    current_breakdown = {row["_id"]["cat"]: abs(row["total"]) for row in await txn_repo.category_breakdown(user.id, current_month)}
    prior_breakdowns = [
        {row["_id"]["cat"]: abs(row["total"]) for row in await txn_repo.category_breakdown(user.id, m)}
        for m in prior_months
    ]
    for cat_id, current_total in current_breakdown.items():
        prior_values = [b.get(cat_id, 0) for b in prior_breakdowns]
        if not prior_values or all(v == 0 for v in prior_values):
            continue
        median_prior = statistics.median(prior_values)
        if median_prior > 0 and current_total > median_prior * 1.5:
            anomalies.append(
                Anomaly(
                    kind="category_spike",
                    message=f"Spending in one category is {format_inr_minor(current_total)} this month, "
                    f"more than 50% above its 3-month median of {format_inr_minor(int(median_prior))}.",
                    severity="warning",
                )
            )

    for c in await commitment_repo.list_confirmed(user.id):
        if len(c.amount_history) >= 2:
            latest, previous = c.amount_history[-1], c.amount_history[-2]
            if previous.amount_minor > 0 and latest.amount_minor > previous.amount_minor * 1.1:
                anomalies.append(
                    Anomaly(
                        kind="commitment_price_increase",
                        message=f"{c.display_name} is {format_inr_minor(latest.amount_minor)} now, "
                        f"up from {format_inr_minor(previous.amount_minor)}.",
                        severity="info",
                    )
                )

    return anomalies
