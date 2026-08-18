from __future__ import annotations

from bson import ObjectId

from app.models.category import Category
from app.repositories.base import Repository


class CategoryRepository(Repository[Category]):
    collection_name = "categories"
    model = Category

    async def get_by_name(self, user_id: ObjectId, name: str) -> Category | None:
        doc = await self.col.find_one(self._scoped(user_id, {"name": name}))
        return Category.model_validate(doc) if doc else None
