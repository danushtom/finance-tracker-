from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter

from app.deps import CurrentUser, DbDep
from app.errors import NotFoundError
from app.models.category import Category
from app.repositories.categories import CategoryRepository
from app.repositories.users import UserRepository
from app.schemas.categories import CategoryCreate, CategoryMerge, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[Category])
async def list_categories(user: CurrentUser, db: DbDep, include_archived: bool = False):
    repo = CategoryRepository(db)
    query = {} if include_archived else {"archived": False}
    return await repo.find(user.id, query, sort=[("sort_order", 1)])


@router.post("", response_model=Category, status_code=201)
async def create_category(body: CategoryCreate, user: CurrentUser, db: DbDep):
    data = body.model_dump(by_alias=True)
    if data.get("parent_id"):
        data["parent_id"] = ObjectId(data["parent_id"])
    category = Category(user_id=user.id, **data)
    await CategoryRepository(db).insert(category)
    await UserRepository(db).bump_data_version(user.id)
    return category


@router.patch("/{category_id}", response_model=Category)
async def update_category(category_id: str, body: CategoryUpdate, user: CurrentUser, db: DbDep):
    repo = CategoryRepository(db)
    updates = body.model_dump(exclude_unset=True, by_alias=True)
    if not await repo.update(user.id, ObjectId(category_id), {"$set": updates}):
        raise NotFoundError("Category")
    await UserRepository(db).bump_data_version(user.id)
    return await repo.get(user.id, ObjectId(category_id))


@router.delete("/{category_id}", status_code=204)
async def archive_category(category_id: str, user: CurrentUser, db: DbDep):
    repo = CategoryRepository(db)
    if not await repo.update(user.id, ObjectId(category_id), {"$set": {"archived": True}}):
        raise NotFoundError("Category")
    await UserRepository(db).bump_data_version(user.id)


@router.post("/{category_id}/merge", status_code=204)
async def merge_category(category_id: str, body: CategoryMerge, user: CurrentUser, db: DbDep):
    """FR-5.6: reassigns all transactions and rules atomically, then
    archives the source category (section 5.3 transaction usage #3)."""
    from_id = ObjectId(category_id)
    into_id = ObjectId(body.into_id)

    repo = CategoryRepository(db)
    into = await repo.get(user.id, into_id)
    if into is None:
        raise NotFoundError("Target category")

    client = db.client
    async with await client.start_session() as session:
        async with session.start_transaction():
            await db.transactions.update_many(
                {"user_id": user.id, "category_id": from_id},
                {"$set": {"category_id": into_id, "category_class": into.class_.value}},
                session=session,
            )
            await db.rules.update_many(
                {"user_id": user.id, "category_id": from_id},
                {"$set": {"category_id": into_id}},
                session=session,
            )
            await db.categories.update_one(
                {"user_id": user.id, "_id": from_id},
                {"$set": {"archived": True}},
                session=session,
            )
    await UserRepository(db).bump_data_version(user.id)
