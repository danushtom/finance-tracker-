from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter

from app.deps import CurrentUser, DbDep
from app.errors import NotFoundError
from app.models.account import Account
from app.repositories.accounts import AccountRepository
from app.repositories.users import UserRepository
from app.schemas.accounts import AccountCreate, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[Account])
async def list_accounts(user: CurrentUser, db: DbDep, include_archived: bool = False):
    repo = AccountRepository(db)
    query = {} if include_archived else {"archived": False}
    return await repo.find(user.id, query, sort=[("created_at", 1)])


@router.post("", response_model=Account, status_code=201)
async def create_account(body: AccountCreate, user: CurrentUser, db: DbDep):
    account = Account(user_id=user.id, **body.model_dump())
    await AccountRepository(db).insert(account)
    await UserRepository(db).bump_data_version(user.id)
    return account


@router.patch("/{account_id}", response_model=Account)
async def update_account(account_id: str, body: AccountUpdate, user: CurrentUser, db: DbDep):
    repo = AccountRepository(db)
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
    if not await repo.update(user.id, ObjectId(account_id), {"$set": updates}):
        raise NotFoundError("Account")
    await UserRepository(db).bump_data_version(user.id)
    return await repo.get(user.id, ObjectId(account_id))


@router.delete("/{account_id}", status_code=204)
async def archive_account(account_id: str, user: CurrentUser, db: DbDep):
    repo = AccountRepository(db)
    if not await repo.update(user.id, ObjectId(account_id), {"$set": {"archived": True}}):
        raise NotFoundError("Account")
    await UserRepository(db).bump_data_version(user.id)
