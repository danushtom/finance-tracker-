from __future__ import annotations

from fastapi import APIRouter

from app.deps import CurrentUser, DbDep
from app.models.merchant import Merchant
from app.repositories.merchants import MerchantRepository

router = APIRouter(prefix="/merchants", tags=["merchants"])


@router.get("", response_model=list[Merchant])
async def list_merchants(user: CurrentUser, db: DbDep, q: str | None = None, limit: int = 100):
    repo = MerchantRepository(db)
    if q:
        return await repo.search(user.id, q, limit=limit)
    return await repo.find(user.id, sort=[("last_seen", -1)], limit=limit)
