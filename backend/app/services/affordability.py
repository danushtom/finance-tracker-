"""Wishlist affordability (FR-9.2, FR-9.4, section 9.4).

Each item is evaluated independently against the same Safe-to-Spend
snapshot (FR-9.3) — buying one item does not silently change the verdict
for others until a purchase is actually recorded.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from datetime import date

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.common import Minor
from app.models.user import User
from app.models.wishlist import WishlistItem
from app.repositories.transactions import TransactionRepository
from app.services.date_utils import last_n_months
from app.services.safe_to_spend import SafeToSpend


@dataclass
class AffordabilityVerdict:
    affordable: bool
    remaining_after_purchase_minor: Minor | None
    shortfall_minor: Minor
    months_to_afford: int | None
    on_current_cash_flow: bool


async def projected_monthly_surplus(
    db: AsyncIOMotorDatabase, user: User, *, today: date | None = None
) -> Minor:
    """baseline income - median fixed - median variable spend of the last 3
    months (FR-9.4, shared with the advisor's FR-11.3 allocation)."""
    today = today or date.today()
    txn_repo = TransactionRepository(db)
    months = last_n_months(today, 3)

    baselines = [await txn_repo.sum_income(user.id, m, income_type="baseline") for m in months]
    fixed = [await txn_repo.sum_outflows(user.id, m, class_="fixed") for m in months]
    variable = [await txn_repo.sum_outflows(user.id, m, class_in=["variable", "isolated"]) for m in months]

    baseline_income = statistics.median(baselines) if baselines else 0
    median_fixed = statistics.median(fixed) if fixed else 0
    median_variable = statistics.median(variable) if variable else 0

    return int(baseline_income - median_fixed - median_variable)


def evaluate_item(item: WishlistItem, sts: SafeToSpend, surplus_minor: Minor) -> AffordabilityVerdict:
    available = sts.display_amount_minor()
    affordable = item.price_minor <= available
    shortfall = max(0, item.price_minor - available)

    months_to_afford: int | None = None
    on_current_cash_flow = surplus_minor > 0
    if not affordable and on_current_cash_flow:
        months_to_afford = math.ceil(shortfall / surplus_minor)

    return AffordabilityVerdict(
        affordable=affordable,
        remaining_after_purchase_minor=(available - item.price_minor) if affordable else None,
        shortfall_minor=shortfall,
        months_to_afford=months_to_afford,
        on_current_cash_flow=on_current_cash_flow,
    )
