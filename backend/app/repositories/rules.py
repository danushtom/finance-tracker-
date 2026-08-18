from __future__ import annotations

from bson import ObjectId

from app.models.rule import Rule
from app.repositories.base import Repository


class RuleRepository(Repository[Rule]):
    collection_name = "rules"
    model = Rule

    async def list_enabled(self, user_id: ObjectId) -> list[Rule]:
        return await self.find(user_id, {"enabled": True}, sort=[("priority", -1)])

    async def find_exact(self, user_id: ObjectId, pattern: str) -> Rule | None:
        doc = await self.col.find_one(
            self._scoped(user_id, {"match_type": "exact", "pattern": pattern, "enabled": True})
        )
        return Rule.model_validate(doc) if doc else None
