"""Safe-to-Spend (FR-8.3) — the most heavily tested file in the project
(NFR-6). Every rupee of the deduction must be traceable to a line item in
the UI (FR-8.2, G-3): every `WaterfallLine` below carries a `drilldown`
descriptor the frontend turns into a filtered transaction link.

    baseline_income_received
  + discretionary_share_of_variable
  ------------------------------------
  = spendable_pool

  - fixed_remaining
  - variable_spent_to_date
  - planned_savings_remaining
  - planned_investment_remaining
  - goal_reservations_remaining
  - buffer
  ------------------------------------
  = SAFE-TO-SPEND

The FR-8.4 worked example is asserted to the paise in
`tests/unit/test_safe_to_spend.py` — that test is the executable
specification for this module.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.common import Minor
from app.models.user import User
from app.repositories.commitments import CommitmentRepository
from app.repositories.goals import GoalRepository
from app.repositories.transactions import TransactionRepository


@dataclass
class WaterfallLine:
    label: str
    amount_minor: Minor
    sign: str  # "+" | "-"
    drilldown: dict | None


@dataclass
class SafeToSpend:
    month: str
    amount_minor: Minor  # may be negative internally
    is_over: bool  # FR-8.3.1 — the UI floors the headline at 0
    per_day_minor: Minor | None
    days_left: int
    lines: list[WaterfallLine] = field(default_factory=list)

    def display_amount_minor(self) -> Minor:
        return max(0, self.amount_minor)

    def over_by_minor(self) -> Minor:
        return abs(min(0, self.amount_minor))


def days_remaining_in_month(month: str, today: date) -> int:
    year, mon = int(month[:4]), int(month[5:7])
    last_day = calendar.monthrange(year, mon)[1]
    if today.year == year and today.month == mon:
        return max(0, last_day - today.day + 1)
    first_of_month = date(year, mon, 1)
    if today < first_of_month:
        return last_day
    return 0  # a past month has no "days remaining"


async def _funded_this_month(goal, month: str) -> Minor:  # noqa: ANN001
    return sum(c.amount_minor for c in goal.contributions if c.date.strftime("%Y-%m") == month)


async def compute_safe_to_spend(
    db: AsyncIOMotorDatabase, user: User, month: str, *, today: date | None = None
) -> SafeToSpend:
    today = today or date.today()
    settings = user.settings
    txn_repo = TransactionRepository(db)
    commitment_repo = CommitmentRepository(db)
    goal_repo = GoalRepository(db)

    lines: list[WaterfallLine] = []

    # --- income side --------------------------------------------------
    baseline_received = await txn_repo.sum_income(user.id, month, income_type="baseline")
    baseline_is_expected = False
    if baseline_received == 0 and settings.count_expected_salary:
        baseline_received = await _expected_baseline(db, user.id, month)  # FR-8.3.4
        baseline_is_expected = baseline_received > 0
    lines.append(
        WaterfallLine(
            label="Baseline income" + (" (expected)" if baseline_is_expected else ""),
            amount_minor=baseline_received,
            sign="+",
            drilldown={"kind": "income", "source_type": "baseline", "month": month},
        )
    )

    # FR-8.3.3: only variable income actually received contributes.
    variable_received = await txn_repo.sum_income(user.id, month, income_type="variable")
    discretionary_pct = settings.variable_split.discretionary_pct
    discretionary = (variable_received * discretionary_pct) // 100
    lines.append(
        WaterfallLine(
            label=f"Project income ({discretionary_pct}% share)",
            amount_minor=discretionary,
            sign="+",
            drilldown={"kind": "income", "source_type": "variable", "month": month},
        )
    )

    spendable = baseline_received + discretionary

    # --- committed / spent side -----------------------------------------
    confirmed_commitments = await commitment_repo.list_confirmed(user.id)
    fixed_due = sum(c.expected_amount_minor for c in confirmed_commitments)
    fixed_paid = await txn_repo.sum_outflows(user.id, month, class_="fixed")
    fixed_left = max(0, fixed_due - fixed_paid)
    lines.append(
        WaterfallLine(
            label="Fixed still due",
            amount_minor=fixed_left,
            sign="-",
            drilldown={"class": "fixed", "unpaid": True, "month": month},
        )
    )

    variable_spent = await txn_repo.sum_outflows(user.id, month, class_in=["variable", "isolated"])
    lines.append(
        WaterfallLine(
            label="Spent so far",
            amount_minor=variable_spent,
            sign="-",
            drilldown={"class": ["variable", "isolated"], "month": month},
        )
    )

    saved_this_month = 0
    goals = await goal_repo.list_active(user.id)
    for goal in goals:
        saved_this_month += await _funded_this_month(goal, month)
    savings_left = max(0, settings.monthly_savings_target_minor - saved_this_month)
    lines.append(
        WaterfallLine(label="Savings not yet moved", amount_minor=savings_left, sign="-", drilldown=None)
    )

    invested_this_month = await txn_repo.sum_outflows(user.id, month, class_="investment")
    investment_left = max(0, settings.monthly_investment_target_minor - invested_this_month)
    lines.append(
        WaterfallLine(label="Investing not yet moved", amount_minor=investment_left, sign="-", drilldown=None)
    )

    goals_left = 0
    for goal in goals:
        funded = await _funded_this_month(goal, month)
        goals_left += max(0, goal.monthly_reservation_minor - funded)
    if goals_left:
        lines.append(
            WaterfallLine(label="Goal reservations remaining", amount_minor=goals_left, sign="-", drilldown=None)
        )

    lines.append(WaterfallLine(label="Buffer", amount_minor=settings.buffer_minor, sign="-", drilldown=None))

    amount = (
        spendable
        - fixed_left
        - variable_spent
        - savings_left
        - investment_left
        - goals_left
        - settings.buffer_minor
    )

    days_left = days_remaining_in_month(month, today)
    per_day = amount // days_left if days_left > 0 and amount > 0 else None

    return SafeToSpend(
        month=month,
        amount_minor=amount,
        is_over=amount < 0,
        per_day_minor=per_day,
        days_left=days_left,
        lines=lines,
    )


async def _expected_baseline(db: AsyncIOMotorDatabase, user_id: ObjectId, month: str) -> Minor:
    from app.models.income import IncomeType
    from app.repositories.income_sources import IncomeSourceRepository

    sources = await IncomeSourceRepository(db).find(user_id, {"type": IncomeType.BASELINE.value, "active": True})
    return sum(s.expected_amount_minor or 0 for s in sources)
