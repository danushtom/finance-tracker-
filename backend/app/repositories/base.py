"""Repository base class.

`Repository` is the only code that talks to Mongo (layering rule #3 in
TECHNICAL_DESIGN.md section 2.2). Every method that reads or writes
user-owned data takes `user_id` as its first argument and injects it into
every filter — there is deliberately no method that can query without it
(NFR-7). `find_one`/`find_many`/`update_one`/`delete_one` all merge
`{"user_id": user_id}` into the filter before it ever reaches Mongo.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pydantic import BaseModel

from app.models.common import to_bson_safe, utcnow

ModelT = TypeVar("ModelT", bound=BaseModel)


class Repository(Generic[ModelT]):
    collection_name: str
    model: type[ModelT]

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db

    @property
    def col(self) -> AsyncIOMotorCollection:
        return self.db[self.collection_name]

    def _scoped(self, user_id: ObjectId, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        f: dict[str, Any] = {"user_id": user_id}
        if extra:
            f.update(extra)
        return f

    async def get(self, user_id: ObjectId, doc_id: ObjectId) -> ModelT | None:
        doc = await self.col.find_one(self._scoped(user_id, {"_id": doc_id}))
        return self.model.model_validate(doc) if doc else None

    async def find(
        self,
        user_id: ObjectId,
        query: dict[str, Any] | None = None,
        *,
        sort: list[tuple[str, int]] | None = None,
        limit: int = 0,
        skip: int = 0,
    ) -> list[ModelT]:
        cursor = self.col.find(self._scoped(user_id, query))
        if sort:
            cursor = cursor.sort(sort)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        return [self.model.model_validate(d) async for d in cursor]

    async def count(self, user_id: ObjectId, query: dict[str, Any] | None = None) -> int:
        return await self.col.count_documents(self._scoped(user_id, query))

    async def insert(self, doc: ModelT, *, session: Any = None) -> ModelT:
        await self.col.insert_one(doc.model_dump(by_alias=True, mode="python"), session=session)
        return doc

    async def update(
        self,
        user_id: ObjectId,
        doc_id: ObjectId,
        update: dict[str, Any],
        *,
        session: Any = None,
    ) -> bool:
        update = to_bson_safe(update)
        update.setdefault("$set", {})["updated_at"] = utcnow()
        result = await self.col.update_one(
            self._scoped(user_id, {"_id": doc_id}), update, session=session
        )
        return result.matched_count > 0

    async def delete(self, user_id: ObjectId, doc_id: ObjectId, *, session: Any = None) -> bool:
        result = await self.col.delete_one(self._scoped(user_id, {"_id": doc_id}), session=session)
        return result.deleted_count > 0
