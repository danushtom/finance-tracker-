from __future__ import annotations

from bson import ObjectId

from app.models.commitment import Commitment, CommitmentStatus
from app.repositories.base import Repository


class CommitmentRepository(Repository[Commitment]):
    collection_name = "commitments"
    model = Commitment

    async def find_by_merchant(self, user_id: ObjectId, merchant_norm: str) -> Commitment | None:
        doc = await self.col.find_one(self._scoped(user_id, {"merchant_norm": merchant_norm}))
        return Commitment.model_validate(doc) if doc else None

    async def list_confirmed(self, user_id: ObjectId) -> list[Commitment]:
        return await self.find(user_id, {"status": CommitmentStatus.CONFIRMED.value})

    async def list_detected(self, user_id: ObjectId) -> list[Commitment]:
        return await self.find(user_id, {"status": CommitmentStatus.DETECTED.value})
