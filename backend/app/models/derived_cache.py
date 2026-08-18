from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.models.common import MongoModel, PyObjectId, utcnow


class DerivedCacheEntry(MongoModel):
    user_id: PyObjectId
    key: str  # e.g. "sts:2026-08"
    version: int
    payload: dict[str, Any] = Field(default_factory=dict)
    computed_at: datetime = Field(default_factory=utcnow)
