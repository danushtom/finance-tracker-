from __future__ import annotations

from app.models.goal import Goal
from app.repositories.base import Repository


class GoalRepository(Repository[Goal]):
    collection_name = "goals"
    model = Goal

    async def list_active(self, user_id):  # noqa: ANN001
        return await self.find(user_id, {"status": "active"})
