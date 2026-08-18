from __future__ import annotations

from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.auth import RefreshToken
from app.models.common import utcnow


class RefreshTokenRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.col = db.refresh_tokens

    async def create(self, token: RefreshToken) -> RefreshToken:
        await self.col.insert_one(token.model_dump(by_alias=True, mode="python"))
        return token

    async def get_by_jti(self, user_id: ObjectId, jti: str) -> RefreshToken | None:
        doc = await self.col.find_one({"user_id": user_id, "jti": jti})
        return RefreshToken.model_validate(doc) if doc else None

    async def find_by_hash(self, token_hash: str) -> RefreshToken | None:
        doc = await self.col.find_one({"token_hash": token_hash})
        return RefreshToken.model_validate(doc) if doc else None

    async def revoke(self, user_id: ObjectId, jti: str, *, at: datetime | None = None) -> None:
        await self.col.update_one(
            {"user_id": user_id, "jti": jti}, {"$set": {"revoked_at": at or utcnow()}}
        )

    async def revoke_all_for_user(self, user_id: ObjectId) -> None:
        await self.col.update_many(
            {"user_id": user_id, "revoked_at": None}, {"$set": {"revoked_at": utcnow()}}
        )

    async def delete_all_for_user(self, user_id: ObjectId) -> None:
        await self.col.delete_many({"user_id": user_id})
