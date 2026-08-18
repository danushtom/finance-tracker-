"""Password hashing and JWT helpers (FR-1.1, FR-1.2).

Access tokens are short-lived HS256 JWTs carrying `sub` (user id), `jti`,
`exp`, `iat`. Refresh tokens are opaque random strings, stored only as a
hash, with rotation and reuse detection (section 10.1).
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import Settings

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def create_access_token(*, user_id: str, settings: Settings) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "jti": str(uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_ttl_min),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str, *, settings: Settings) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


def generate_refresh_token() -> tuple[str, str, str]:
    """Returns (raw_token, jti, token_hash). Only the hash is persisted."""
    raw = secrets.token_urlsafe(48)
    jti = str(uuid4())
    return raw, jti, hash_refresh_token(raw)


def hash_refresh_token(raw: str) -> str:
    return sha256(raw.encode()).hexdigest()
