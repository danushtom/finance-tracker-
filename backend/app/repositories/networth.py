from __future__ import annotations

from bson import ObjectId

from app.models.networth import NetWorthSnapshot
from app.repositories.base import Repository


class NetWorthRepository(Repository[NetWorthSnapshot]):
    collection_name = "net_worth_snapshots"
    model = NetWorthSnapshot

    async def upsert_month(self, snapshot: NetWorthSnapshot) -> None:
        await self.col.update_one(
            self._scoped(snapshot.user_id, {"month": snapshot.month}),
            {"$set": snapshot.model_dump(by_alias=True, mode="python", exclude={"id"})},
            upsert=True,
        )

    async def history(self, user_id: ObjectId, limit: int = 12) -> list[NetWorthSnapshot]:
        return await self.find(user_id, sort=[("month", -1)], limit=limit)
