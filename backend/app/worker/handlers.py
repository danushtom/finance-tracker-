"""Job handlers (section 12): process_import, backfill_rule,
detect_recurring, snapshot_networth."""

from __future__ import annotations

import structlog
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import Settings
from app.models.job import Job
from app.parsers.base import ColumnMapping
from app.repositories.imports import ImportRepository
from app.repositories.rules import RuleRepository
from app.repositories.transactions import TransactionRepository
from app.services import import_service, networth, recurring

log = structlog.get_logger(__name__)


async def handle_process_import(db: AsyncIOMotorDatabase, settings: Settings, job: Job) -> None:
    import_id = ObjectId(job.payload["import_id"])
    import_doc = await ImportRepository(db).get(job.user_id, import_id)
    if import_doc is None:
        log.warning("process_import_missing_import", import_id=str(import_id))
        return
    mapping_dict = job.payload.get("mapping")
    mapping = ColumnMapping.from_dict(mapping_dict) if mapping_dict else None
    await import_service.run_import(db, settings, import_doc, mapping=mapping)


async def handle_backfill_rule(db: AsyncIOMotorDatabase, settings: Settings, job: Job) -> None:
    """FR-4.8: retroactively recategorise past transactions matching a
    newly created rule. Never touches user-set categories (FR-4.7)."""
    from app.categorise.rules import RuleSet

    rule_id = ObjectId(job.payload["rule_id"])
    rule = await RuleRepository(db).get(job.user_id, rule_id)
    if rule is None:
        return

    rule_set = RuleSet([rule])
    txn_repo = TransactionRepository(db)
    candidates = await txn_repo.find(job.user_id, {"categorised_by": {"$ne": "user"}}, limit=0)
    matched_ids = [t.id for t in candidates if rule_set.match(t.merchant_norm, direction=t.direction, amount_minor=t.amount_minor)]

    if matched_ids:
        await db.transactions.update_many(
            {"user_id": job.user_id, "_id": {"$in": matched_ids}},
            {
                "$set": {
                    "category_id": rule.category_id,
                    "subcategory_id": rule.subcategory_id,
                    "categorised_by": "rule",
                    "confidence": 95,
                    "needs_review": False,
                }
            },
        )
    log.info("backfill_rule_completed", rule_id=str(rule_id), matched=len(matched_ids))


async def handle_detect_recurring(db: AsyncIOMotorDatabase, settings: Settings, job: Job) -> None:
    await recurring.detect_recurring_commitments(db, job.user_id)


async def handle_snapshot_networth(db: AsyncIOMotorDatabase, settings: Settings, job: Job) -> None:
    await networth.snapshot_current_month(db, job.user_id)


HANDLERS = {
    "process_import": handle_process_import,
    "backfill_rule": handle_backfill_rule,
    "detect_recurring": handle_detect_recurring,
    "snapshot_networth": handle_snapshot_networth,
}
