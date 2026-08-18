"""Motor client and index bootstrap.

Index creation is idempotent and runs on API startup (see `app.main`), per
TECHNICAL_DESIGN.md section 15. `ensure_indexes` is also called at the start
of the integration test suite against a fresh testcontainers Mongo.
"""

from __future__ import annotations

import structlog
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, TEXT

from app.config import get_settings

log = structlog.get_logger(__name__)

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncIOMotorClient(settings.mongodb_uri, uuidRepresentation="standard")
    return _client


def get_database() -> AsyncIOMotorDatabase:
    global _db
    if _db is None:
        settings = get_settings()
        _db = get_client()[settings.mongodb_db]
    return _db


async def close_client() -> None:
    global _client, _db
    if _client is not None:
        _client.close()
    _client = None
    _db = None


async def assert_replica_set(db: AsyncIOMotorDatabase) -> None:
    """C-1 / ADR-7: multi-document transactions require a replica set.

    Fails fast with a clear message rather than letting an import silently
    run non-atomically (see Risks table in TECHNICAL_DESIGN.md section 18).
    """
    try:
        await db.client.admin.command("replSetGetStatus")
    except Exception as exc:  # noqa: BLE001 - we want to convert *any* failure
        raise RuntimeError(
            "MongoDB is not running as a replica set. Multi-document transactions "
            "(required for atomic imports) are unavailable. Start mongod with "
            "--replSet rs0 and run rs.initiate(), or use `docker compose up`."
        ) from exc


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db.users.create_index([("email", ASCENDING)], unique=True)

    await db.refresh_tokens.create_index([("user_id", ASCENDING), ("jti", ASCENDING)], unique=True)
    await db.refresh_tokens.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0)

    await db.accounts.create_index([("user_id", ASCENDING), ("archived", ASCENDING)])

    await db.categories.create_index(
        [("user_id", ASCENDING), ("archived", ASCENDING), ("sort_order", ASCENDING)]
    )
    await db.categories.create_index([("user_id", ASCENDING), ("parent_id", ASCENDING)])

    await db.merchants.create_index([("user_id", ASCENDING), ("merchant_norm", ASCENDING)], unique=True)

    await db.rules.create_index([("user_id", ASCENDING), ("enabled", ASCENDING), ("priority", DESCENDING)])
    await db.rules.create_index([("user_id", ASCENDING), ("match_type", ASCENDING), ("pattern", ASCENDING)])

    await db.imports.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])

    txns = db.transactions
    await txns.create_index([("user_id", ASCENDING), ("date", DESCENDING)])
    await txns.create_index([("user_id", ASCENDING), ("fingerprint", ASCENDING)], unique=True)
    await txns.create_index([("user_id", ASCENDING), ("date", DESCENDING), ("category_class", ASCENDING)])
    await txns.create_index([("user_id", ASCENDING), ("category_id", ASCENDING), ("date", DESCENDING)])
    await txns.create_index([("user_id", ASCENDING), ("merchant_norm", ASCENDING), ("date", DESCENDING)])
    await txns.create_index([("user_id", ASCENDING), ("needs_review", ASCENDING), ("date", DESCENDING)])
    await txns.create_index([("user_id", ASCENDING), ("account_id", ASCENDING), ("date", DESCENDING)])
    await txns.create_index([("user_id", ASCENDING), ("import_id", ASCENDING)])
    await txns.create_index([("user_id", ASCENDING), ("description_raw", TEXT)])

    await db.income_sources.create_index([("user_id", ASCENDING), ("active", ASCENDING)])

    await db.commitments.create_index(
        [("user_id", ASCENDING), ("status", ASCENDING), ("next_expected_date", ASCENDING)]
    )

    await db.goals.create_index([("user_id", ASCENDING), ("status", ASCENDING)])

    await db.wishlist_items.create_index([("user_id", ASCENDING), ("status", ASCENDING)])

    await db.investments.create_index([("user_id", ASCENDING), ("archived", ASCENDING)])

    await db.net_worth_snapshots.create_index([("user_id", ASCENDING), ("month", DESCENDING)], unique=True)

    await db.llm_cache.create_index(
        [("user_id", ASCENDING), ("merchant_norm", ASCENDING), ("prompt_version", ASCENDING)], unique=True
    )

    await db.jobs.create_index([("status", ASCENDING), ("created_at", ASCENDING)])
    await db.jobs.create_index([("locked_at", ASCENDING)])

    await db.derived_cache.create_index([("user_id", ASCENDING), ("key", ASCENDING)], unique=True)

    await db.allocations.create_index([("user_id", ASCENDING), ("transaction_id", ASCENDING)], unique=True)

    log.info("indexes_ensured")
