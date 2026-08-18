from __future__ import annotations

from datetime import datetime

from app.models.common import MongoModel, PyObjectId


class RefreshToken(MongoModel):
    user_id: PyObjectId
    jti: str
    token_hash: str
    expires_at: datetime
    revoked_at: datetime | None = None
    user_agent: str | None = None
