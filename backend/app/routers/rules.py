from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter

from app.deps import CurrentUser, DbDep
from app.errors import NotFoundError
from app.models.job import Job, JobType
from app.models.rule import MatchType, Rule, RuleSource
from app.repositories.jobs import JobRepository
from app.repositories.rules import RuleRepository
from app.repositories.transactions import TransactionRepository
from app.repositories.users import UserRepository
from app.schemas.rules import RuleCreate, RulePreviewRequest, RulePreviewResponse, RuleUpdate

router = APIRouter(prefix="/rules", tags=["rules"])


def _match_query(match_type: MatchType, pattern: str, direction: str | None,
                  amount_min_minor: int | None, amount_max_minor: int | None) -> dict:
    query: dict = {}
    if match_type == MatchType.EXACT:
        query["merchant_norm"] = pattern.upper()
    elif match_type == MatchType.CONTAINS:
        query["merchant_norm"] = {"$regex": pattern.upper(), "$options": "i"}
    elif match_type == MatchType.STARTS_WITH:
        query["merchant_norm"] = {"$regex": f"^{pattern.upper()}", "$options": "i"}
    else:
        query["merchant_norm"] = {"$regex": pattern, "$options": "i"}
    if direction:
        query["direction"] = direction
    if amount_min_minor is not None or amount_max_minor is not None:
        amt: dict = {}
        if amount_min_minor is not None:
            amt["$gte"] = amount_min_minor
        if amount_max_minor is not None:
            amt["$lte"] = amount_max_minor
        query["amount_minor"] = amt
    return query


@router.get("", response_model=list[Rule])
async def list_rules(user: CurrentUser, db: DbDep):
    return await RuleRepository(db).find(user.id, sort=[("priority", -1)])


@router.post("", response_model=Rule, status_code=201)
async def create_rule(body: RuleCreate, user: CurrentUser, db: DbDep):
    pattern = body.pattern.upper() if body.match_type != MatchType.REGEX else body.pattern
    rule = Rule(
        user_id=user.id,
        match_type=body.match_type,
        pattern=pattern,
        direction=body.direction,
        amount_min_minor=body.amount_min_minor,
        amount_max_minor=body.amount_max_minor,
        category_id=ObjectId(body.category_id),
        subcategory_id=ObjectId(body.subcategory_id) if body.subcategory_id else None,
        kind_override=body.kind_override,
        priority=body.priority,
        source=RuleSource.USER,
    )
    await RuleRepository(db).insert(rule)
    await UserRepository(db).bump_data_version(user.id)

    if body.backfill:
        job = Job(
            user_id=user.id,
            type=JobType.BACKFILL_RULE,
            payload={"rule_id": str(rule.id)},
        )
        await JobRepository(db).enqueue(job)

    return rule


@router.post("/preview", response_model=RulePreviewResponse)
async def preview_rule(body: RulePreviewRequest, user: CurrentUser, db: DbDep):
    txn_repo = TransactionRepository(db)
    query = _match_query(body.match_type, body.pattern, body.direction, body.amount_min_minor, body.amount_max_minor)
    count = await txn_repo.count_matching(user.id, query)
    sample_txns = await txn_repo.find(user.id, {**query, "categorised_by": {"$ne": "user"}}, limit=5)
    return RulePreviewResponse(affected_count=count, sample=[t.description_raw for t in sample_txns])


@router.patch("/{rule_id}", response_model=Rule)
async def update_rule(rule_id: str, body: RuleUpdate, user: CurrentUser, db: DbDep):
    repo = RuleRepository(db)
    updates = body.model_dump(exclude_unset=True)
    if "category_id" in updates and updates["category_id"]:
        updates["category_id"] = ObjectId(updates["category_id"])
    if "subcategory_id" in updates and updates["subcategory_id"]:
        updates["subcategory_id"] = ObjectId(updates["subcategory_id"])
    if not await repo.update(user.id, ObjectId(rule_id), {"$set": updates}):
        raise NotFoundError("Rule")
    await UserRepository(db).bump_data_version(user.id)
    return await repo.get(user.id, ObjectId(rule_id))


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(rule_id: str, user: CurrentUser, db: DbDep):
    if not await RuleRepository(db).delete(user.id, ObjectId(rule_id)):
        raise NotFoundError("Rule")
    await UserRepository(db).bump_data_version(user.id)
