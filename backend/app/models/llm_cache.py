from __future__ import annotations

from app.models.common import PyObjectId, UserScopedModel


class LLMCacheEntry(UserScopedModel):
    merchant_norm: str
    category_id: PyObjectId
    confidence: int
    model: str
    prompt_version: str
