from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter

from app.deps import CurrentUser, DbDep
from app.errors import NotFoundError, ValidationProblem
from app.models.goal import Goal
from app.models.wishlist import WishlistItem
from app.repositories.goals import GoalRepository
from app.repositories.users import UserRepository
from app.repositories.wishlist import WishlistRepository
from app.schemas.wishlist import (
    SimulateRequest,
    SimulateResponse,
    WishlistItemCreate,
    WishlistItemUpdate,
    WishlistVerdict,
)
from app.services.affordability import evaluate_item, projected_monthly_surplus
from app.services.dashboard_service import get_safe_to_spend_cached

router = APIRouter(prefix="/wishlist", tags=["wishlist"])


async def _verdict_for(item: WishlistItem, sts, surplus) -> WishlistVerdict:  # noqa: ANN001
    v = evaluate_item(item, sts, surplus)
    return WishlistVerdict(
        item_id=str(item.id),
        name=item.name,
        price_minor=item.price_minor,
        priority=item.priority,
        affordable=v.affordable,
        remaining_after_purchase_minor=v.remaining_after_purchase_minor,
        shortfall_minor=v.shortfall_minor,
        months_to_afford=v.months_to_afford,
        on_current_cash_flow=v.on_current_cash_flow,
    )


@router.get("")
async def list_wishlist(user: CurrentUser, db: DbDep, month: str | None = None):
    from datetime import date

    repo = WishlistRepository(db)
    items = await repo.find(user.id, {"status": "wanted"}, sort=[("created_at", 1)])
    sts = await get_safe_to_spend_cached(db, user, month or f"{date.today():%Y-%m}")
    surplus = await projected_monthly_surplus(db, user)
    return [await _verdict_for(item, sts, surplus) for item in items]


@router.post("", response_model=WishlistItem, status_code=201)
async def create_wishlist_item(body: WishlistItemCreate, user: CurrentUser, db: DbDep):
    item = WishlistItem(user_id=user.id, **body.model_dump())
    await WishlistRepository(db).insert(item)
    await UserRepository(db).bump_data_version(user.id)
    return item


@router.patch("/{item_id}", response_model=WishlistItem)
async def update_wishlist_item(item_id: str, body: WishlistItemUpdate, user: CurrentUser, db: DbDep):
    repo = WishlistRepository(db)
    updates = body.model_dump(exclude_unset=True)
    if not await repo.update(user.id, ObjectId(item_id), {"$set": updates}):
        raise NotFoundError("Wishlist item")
    await UserRepository(db).bump_data_version(user.id)
    return await repo.get(user.id, ObjectId(item_id))


@router.delete("/{item_id}", status_code=204)
async def delete_wishlist_item(item_id: str, user: CurrentUser, db: DbDep):
    if not await WishlistRepository(db).delete(user.id, ObjectId(item_id)):
        raise NotFoundError("Wishlist item")
    await UserRepository(db).bump_data_version(user.id)


@router.post("/simulate", response_model=SimulateResponse)
async def simulate(body: SimulateRequest, user: CurrentUser, db: DbDep):
    """FR-9.5: "what if I buy these together?" — combined verdict ordered
    by priority."""
    from datetime import date

    repo = WishlistRepository(db)
    items = [await repo.get(user.id, ObjectId(i)) for i in body.item_ids]
    items = [i for i in items if i is not None]
    items.sort(key=lambda i: {"high": 0, "medium": 1, "low": 2}.get(i.priority, 3))

    sts = await get_safe_to_spend_cached(db, user, f"{date.today():%Y-%m}")
    surplus = await projected_monthly_surplus(db, user)

    verdicts = [await _verdict_for(item, sts, surplus) for item in items]
    combined_total = sum(item.price_minor for item in items)
    available = sts.display_amount_minor()
    combined_affordable = combined_total <= available
    remaining = available - combined_total if combined_affordable else None

    return SimulateResponse(
        items=verdicts,
        combined_affordable=combined_affordable,
        combined_total_minor=combined_total,
        remaining_after_all_minor=remaining,
    )


@router.post("/{item_id}/promote", response_model=Goal)
async def promote_to_goal(item_id: str, user: CurrentUser, db: DbDep):
    """FR-9.6: promote a wishlist item to a Goal in one action, carrying
    over name, target amount and target date."""
    from datetime import date, datetime

    wishlist_repo = WishlistRepository(db)
    item = await wishlist_repo.get(user.id, ObjectId(item_id))
    if item is None:
        raise NotFoundError("Wishlist item")

    target_date = None
    if item.target_month:
        year, month = int(item.target_month[:4]), int(item.target_month[5:7])
        target_date = date(year, month, 1)

    goal = Goal(
        user_id=user.id,
        name=item.name,
        target_amount_minor=item.price_minor,
        target_date=target_date,
        priority=item.priority,
    )
    await GoalRepository(db).insert(goal)
    await wishlist_repo.update(user.id, item.id, {"$set": {"goal_id": goal.id}})
    await UserRepository(db).bump_data_version(user.id)
    return goal


@router.post("/{item_id}/mark-purchased", response_model=WishlistItem)
async def mark_purchased(item_id: str, user: CurrentUser, db: DbDep, transaction_id: str | None = None):
    """FR-9.7: links the item to the matching transaction and archives it."""
    repo = WishlistRepository(db)
    updates: dict = {"status": "purchased"}
    if transaction_id:
        updates["purchased_transaction_id"] = ObjectId(transaction_id)
    if not await repo.update(user.id, ObjectId(item_id), {"$set": updates}):
        raise NotFoundError("Wishlist item")
    await UserRepository(db).bump_data_version(user.id)
    return await repo.get(user.id, ObjectId(item_id))
