from __future__ import annotations

from fastapi import APIRouter

from app.deps import CurrentUser, DbDep
from app.repositories.networth import NetWorthRepository
from app.services.networth import compute_current_net_worth

router = APIRouter(prefix="/net-worth", tags=["net-worth"])


@router.get("")
async def get_net_worth(user: CurrentUser, db: DbDep):
    assets, liabilities, breakdown = await compute_current_net_worth(db, user.id)
    history = await NetWorthRepository(db).history(user.id, limit=12)
    return {
        "assets_minor": assets,
        "liabilities_minor": liabilities,
        "net_worth_minor": assets - liabilities,
        "breakdown": breakdown,
        "history": list(reversed(history)),
    }
