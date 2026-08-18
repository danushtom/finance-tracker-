"""Net worth = sum(assets) - sum(liabilities) (FR-13.3), snapshotted monthly
so a trend line can be drawn (FR-13.4)."""

from __future__ import annotations

from datetime import date

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.common import Minor
from app.models.networth import NetWorthBreakdownEntry, NetWorthSnapshot
from app.repositories.accounts import AccountRepository
from app.repositories.investments import InvestmentRepository
from app.repositories.networth import NetWorthRepository


async def compute_current_net_worth(
    db: AsyncIOMotorDatabase, user_id: ObjectId
) -> tuple[Minor, Minor, list[NetWorthBreakdownEntry]]:
    account_repo = AccountRepository(db)
    investment_repo = InvestmentRepository(db)

    accounts = await account_repo.find(user_id, {"archived": False})
    investments = await investment_repo.find(user_id, {"archived": False})

    breakdown: list[NetWorthBreakdownEntry] = []
    assets = 0
    liabilities = 0

    for acc in accounts:
        breakdown.append(NetWorthBreakdownEntry(account_id=acc.id, type=acc.type.value, value_minor=acc.current_balance_minor))
        if acc.is_asset:
            assets += acc.current_balance_minor
        else:
            liabilities += abs(acc.current_balance_minor)

    for inv in investments:
        assets += inv.current_value_minor

    return assets, liabilities, breakdown


async def snapshot_current_month(db: AsyncIOMotorDatabase, user_id: ObjectId) -> NetWorthSnapshot:
    assets, liabilities, breakdown = await compute_current_net_worth(db, user_id)
    month = f"{date.today():%Y-%m}"
    snapshot = NetWorthSnapshot(
        user_id=user_id,
        month=month,
        assets_minor=assets,
        liabilities_minor=liabilities,
        net_worth_minor=assets - liabilities,
        breakdown=breakdown,
    )
    await NetWorthRepository(db).upsert_month(snapshot)
    return snapshot
