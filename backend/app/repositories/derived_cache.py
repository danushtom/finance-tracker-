"""Version-based cache invalidation for derived numbers (FR-8.3.6, ADR-5).

No TTL: a `derived_cache` row is only ever trusted if its `version` equals
the user's *current* `data_version`. There is deliberately no time-based
staleness check — correctness of the headline number is not left to a timer.
"""

from __future__ import annotations

from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.common import utcnow
from app.models.derived_cache import DerivedCacheEntry


class DerivedCacheRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.col = db.derived_cache

    async def get(self, user_id: ObjectId, key: str, current_version: int) -> dict[str, Any] | None:
        doc = await self.col.find_one({"user_id": user_id, "key": key})
        if doc and doc["version"] == current_version:
            return doc["payload"]
        return None

    async def put(self, user_id: ObjectId, key: str, version: int, payload: dict[str, Any]) -> None:
        await self.col.update_one(
            {"user_id": user_id, "key": key},
            {"$set": {"version": version, "payload": payload, "computed_at": utcnow()}},
            upsert=True,
        )

    async def invalidate(self, user_id: ObjectId, key: str) -> None:
        await self.col.delete_one({"user_id": user_id, "key": key})
