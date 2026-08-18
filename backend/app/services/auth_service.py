"""Registration, login, token rotation (FR-1). Passwords are hashed with
Argon2id; plaintext is never stored or logged (FR-1.1)."""

from __future__ import annotations

from datetime import timedelta

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import Settings
from app.errors import ConflictError, ForbiddenError, UnauthorizedError
from app.models.auth import RefreshToken
from app.models.common import utcnow
from app.models.user import User
from app.repositories.refresh_tokens import RefreshTokenRepository
from app.repositories.users import UserRepository
from app.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.services.seed import seed_new_user


class InvalidInviteCodeError(ForbiddenError):
    def __init__(self) -> None:
        super().__init__("Invalid or missing invite code")


async def register(
    db: AsyncIOMotorDatabase,
    *,
    email: str,
    password: str,
    display_name: str,
    invite_code: str | None,
    settings: Settings,
) -> User:
    # FR-1.8: a self-hosted instance is not open to the internet by default.
    if settings.registration_invite_code and invite_code != settings.registration_invite_code:
        raise InvalidInviteCodeError()

    user_repo = UserRepository(db)
    existing = await user_repo.get_by_email(email)
    if existing:
        raise ConflictError("Account already exists", detail="An account with this email already exists.")

    user = User(email=email.lower(), password_hash=hash_password(password), display_name=display_name)
    await user_repo.create(user)
    await seed_new_user(db, user.id)
    return user


async def login(
    db: AsyncIOMotorDatabase, *, email: str, password: str
) -> User:
    user = await UserRepository(db).get_by_email(email)
    if user is None or not verify_password(password, user.password_hash):
        raise UnauthorizedError("Invalid email or password")
    return user


async def issue_tokens(
    db: AsyncIOMotorDatabase, *, user: User, settings: Settings, user_agent: str | None
) -> tuple[str, str]:
    """Returns (access_token, raw_refresh_token)."""
    access_token = create_access_token(user_id=str(user.id), settings=settings)
    raw_refresh, jti, token_hash = generate_refresh_token()
    refresh_token = RefreshToken(
        user_id=user.id,
        jti=jti,
        token_hash=token_hash,
        expires_at=utcnow() + timedelta(days=settings.jwt_refresh_ttl_days),
        user_agent=user_agent,
    )
    await RefreshTokenRepository(db).create(refresh_token)
    return access_token, raw_refresh


async def refresh_access_token(
    db: AsyncIOMotorDatabase, *, raw_refresh_token: str, settings: Settings, user_agent: str | None
) -> tuple[str, str, User]:
    """Rotates the refresh token; reuse of a revoked token revokes the whole
    family (section 10.1)."""
    token_repo = RefreshTokenRepository(db)
    token_hash = hash_refresh_token(raw_refresh_token)
    existing = await token_repo.find_by_hash(token_hash)
    if existing is None:
        raise UnauthorizedError("Invalid refresh token")

    if existing.revoked_at is not None or existing.expires_at < utcnow():
        # Reuse of an already-revoked (or expired) token: revoke the whole
        # family defensively.
        await token_repo.revoke_all_for_user(existing.user_id)
        raise UnauthorizedError("Refresh token has been revoked; please log in again")

    user = await UserRepository(db).get_by_id(existing.user_id)
    if user is None:
        raise UnauthorizedError("User not found")

    await token_repo.revoke(existing.user_id, existing.jti)
    access_token, raw_new_refresh = await issue_tokens(
        db, user=user, settings=settings, user_agent=user_agent
    )
    return access_token, raw_new_refresh, user


async def logout(db: AsyncIOMotorDatabase, *, raw_refresh_token: str) -> None:
    token_repo = RefreshTokenRepository(db)
    token_hash = hash_refresh_token(raw_refresh_token)
    existing = await token_repo.find_by_hash(token_hash)
    if existing:
        await token_repo.revoke(existing.user_id, existing.jti)


async def change_password(
    db: AsyncIOMotorDatabase, *, user: User, current_password: str, new_password: str
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise UnauthorizedError("Current password is incorrect")
    user_repo = UserRepository(db)
    await user_repo.update(user.id, {"$set": {"password_hash": hash_password(new_password)}})
    # FR-1.5: revokes all existing refresh tokens.
    await RefreshTokenRepository(db).revoke_all_for_user(user.id)


async def delete_account(db: AsyncIOMotorDatabase, *, user_id: ObjectId) -> None:
    """Hard-deletes the user and all associated data in one operation
    (FR-1.6). Every user-scoped collection is cleared."""
    user_scoped_collections = [
        "accounts", "categories", "merchants", "rules", "imports", "transactions",
        "income_sources", "commitments", "goals", "wishlist_items", "investments",
        "net_worth_snapshots", "llm_cache", "jobs", "derived_cache",
    ]
    for name in user_scoped_collections:
        await db[name].delete_many({"user_id": user_id})
    await RefreshTokenRepository(db).delete_all_for_user(user_id)
    await UserRepository(db).delete(user_id)
