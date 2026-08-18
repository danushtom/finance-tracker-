from __future__ import annotations

from bson import ObjectId

from app.models.allocation import Allocation
from app.repositories.base import Repository


class AllocationRepository(Repository[Allocation]):
    collection_name = "allocations"
    model = Allocation

    async def get_by_transaction(self, user_id: ObjectId, transaction_id: ObjectId) -> Allocation | None:
        doc = await self.col.find_one(self._scoped(user_id, {"transaction_id": transaction_id}))
        return Allocation.model_validate(doc) if doc else None
