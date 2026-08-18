from __future__ import annotations

from datetime import datetime

from bson import ObjectId

from app.models.common import Minor
from app.models.merchant import Merchant, MerchantSource
from app.repositories.base import Repository


class MerchantRepository(Repository[Merchant]):
    collection_name = "merchants"
    model = Merchant

    async def get_by_norm(self, user_id: ObjectId, merchant_norm: str) -> Merchant | None:
        doc = await self.col.find_one(self._scoped(user_id, {"merchant_norm": merchant_norm}))
        return Merchant.model_validate(doc) if doc else None

    async def upsert(
        self,
        user_id: ObjectId,
        merchant_norm: str,
        *,
        display_name: str,
        category_id: ObjectId | None,
        subcategory_id: ObjectId | None,
        confidence: int,
        source: MerchantSource,
        seen_at: datetime,
        amount_minor: Minor,
    ) -> None:
        await self.col.update_one(
            self._scoped(user_id, {"merchant_norm": merchant_norm}),
            {
                "$set": {
                    "display_name": display_name,
                    "category_id": category_id,
                    "subcategory_id": subcategory_id,
                    "confidence": confidence,
                    "source": source.value,
                    "last_seen": seen_at,
                    "updated_at": seen_at,
                },
                "$setOnInsert": {"first_seen": seen_at, "created_at": seen_at},
                "$inc": {"txn_count": 1, "total_minor": abs(amount_minor)},
            },
            upsert=True,
        )

    async def search(self, user_id: ObjectId, q: str, limit: int = 50) -> list[Merchant]:
        cursor = self.col.find(
            self._scoped(user_id, {"merchant_norm": {"$regex": q, "$options": "i"}})
        ).limit(limit)
        return [Merchant.model_validate(d) async for d in cursor]
