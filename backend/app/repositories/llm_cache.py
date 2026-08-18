from __future__ import annotations

from bson import ObjectId

from app.models.llm_cache import LLMCacheEntry
from app.repositories.base import Repository


class LLMCacheRepository(Repository[LLMCacheEntry]):
    collection_name = "llm_cache"
    model = LLMCacheEntry

    async def get(
        self, user_id: ObjectId, merchant_norm: str, prompt_version: str
    ) -> LLMCacheEntry | None:
        doc = await self.col.find_one(
            self._scoped(user_id, {"merchant_norm": merchant_norm, "prompt_version": prompt_version})
        )
        return LLMCacheEntry.model_validate(doc) if doc else None

    async def put(self, entry: LLMCacheEntry) -> None:
        await self.col.update_one(
            self._scoped(
                entry.user_id,
                {"merchant_norm": entry.merchant_norm, "prompt_version": entry.prompt_version},
            ),
            {"$set": entry.model_dump(by_alias=True, mode="python", exclude={"id"})},
            upsert=True,
        )
