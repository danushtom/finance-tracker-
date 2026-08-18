"""Users are the one collection not itself scoped by `user_id` (it IS the
user) — see NFR-7 note in TECHNICAL_DESIGN.md section 5.1."""

from __future__ import annotations

from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.common import utcnow
from app.models.user import User


class UserRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.col = db.users

    async def get_by_id(self, user_id: ObjectId) -> User | None:
        doc = await self.col.find_one({"_id": user_id})
        return User.model_validate(doc) if doc else None

    async def get_by_email(self, email: str) -> User | None:
        doc = await self.col.find_one({"email": email.lower()})
        return User.model_validate(doc) if doc else None

    async def create(self, user: User) -> User:
        user.email = user.email.lower()
        await self.col.insert_one(user.model_dump(by_alias=True, mode="python"))
        return user

    async def update(self, user_id: ObjectId, update: dict[str, Any]) -> bool:
        update.setdefault("$set", {})["updated_at"] = utcnow()
        result = await self.col.update_one({"_id": user_id}, update)
        return result.matched_count > 0

    async def bump_data_version(self, user_id: ObjectId) -> None:
        """Called on every mutating write for this user (FR-8.3.6)."""
        await self.col.update_one({"_id": user_id}, {"$inc": {"data_version": 1}})

    async def delete(self, user_id: ObjectId) -> bool:
        result = await self.col.delete_one({"_id": user_id})
        return result.deleted_count > 0

    async def increment_llm_calls(self, user_id: ObjectId, month: str, by: int = 1) -> int:
        """Resets the counter when the month rolls over; returns the new count."""
        user = await self.get_by_id(user_id)
        if user is None:
            return 0
        if user.llm_calls_month != month:
            await self.col.update_one(
                {"_id": user_id},
                {"$set": {"llm_calls_month": month, "llm_calls_this_month": by}},
            )
            return by
        result = await self.col.find_one_and_update(
            {"_id": user_id},
            {"$inc": {"llm_calls_this_month": by}},
            return_document=True,
        )
        return int(result["llm_calls_this_month"]) if result else by
