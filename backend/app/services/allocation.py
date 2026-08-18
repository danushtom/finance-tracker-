"""Variable-income allocation proposals (FR-12).

On detecting a credit matched to a `variable` income source, propose a
split using `split_minor` — paise-exact, no remainder lost (ADR-2 sibling
rule in section 6). Only the discretionary slice ever reaches Safe-to-Spend
(FR-12.2, enforced independently in `app.services.safe_to_spend` via
`variable_split.discretionary_pct` — this module's persisted proposal is
for user visibility/override and plan-vs-actual tracking, not itself an
input to the Safe-to-Spend formula).
"""

from __future__ import annotations

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.allocation import Allocation
from app.models.user import VariableSplit
from app.parsers.money import split_minor
from app.repositories.allocations import AllocationRepository


async def propose_allocation(
    db: AsyncIOMotorDatabase,
    *,
    user_id: ObjectId,
    transaction_id: ObjectId,
    month: str,
    amount_minor: int,
    split: VariableSplit,
) -> Allocation:
    invest, goals, discretionary = split_minor(
        amount_minor, [split.invest_pct, split.goals_pct, split.discretionary_pct]
    )
    allocation = Allocation(
        user_id=user_id,
        transaction_id=transaction_id,
        month=month,
        total_minor=amount_minor,
        proposed_invest_minor=invest,
        proposed_goals_minor=goals,
        proposed_discretionary_minor=discretionary,
    )
    await AllocationRepository(db).insert(allocation)
    return allocation


def projected_value(amount_minor: int, years: int, annual_rate_pct: float) -> int:
    """FR-12.5: "₹50,000 invested is worth ~₹X in 10 years at 10%." Any
    projection states its assumed rate and that returns are not
    guaranteed — enforced by always returning the rate alongside the
    number at the call site, never silently."""
    return int(amount_minor * ((1 + annual_rate_pct / 100) ** years))
