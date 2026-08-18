from __future__ import annotations

from app.models.import_job import Import
from app.repositories.base import Repository


class ImportRepository(Repository[Import]):
    collection_name = "imports"
    model = Import

    async def list_recent(self, user_id, limit: int = 50):  # noqa: ANN001
        return await self.find(user_id, sort=[("created_at", -1)], limit=limit)
