"""NFR-7: a test suite asserts cross-user isolation. This exercises the
repository layer directly (every repository method takes `user_id` first
and injects it into the filter) — the equivalent HTTP-level sweep
("hit every endpoint as user B with user A's resource IDs, assert 404")
belongs alongside it once the router surface is stable enough to enumerate
mechanically without becoming a maintenance burden on its own."""

from __future__ import annotations

from bson import ObjectId

from app.models.account import Account, AccountType
from app.repositories.accounts import AccountRepository


async def test_user_cannot_read_another_users_account(db) -> None:  # noqa: ANN001
    repo = AccountRepository(db)
    user_a, user_b = ObjectId(), ObjectId()

    account = Account(user_id=user_a, name="HDFC Savings", type=AccountType.BANK)
    await repo.insert(account)

    assert await repo.get(user_a, account.id) is not None
    assert await repo.get(user_b, account.id) is None


async def test_user_cannot_update_another_users_account(db) -> None:  # noqa: ANN001
    repo = AccountRepository(db)
    user_a, user_b = ObjectId(), ObjectId()

    account = Account(user_id=user_a, name="HDFC Savings", type=AccountType.BANK)
    await repo.insert(account)

    updated = await repo.update(user_b, account.id, {"$set": {"name": "Hijacked"}})
    assert updated is False

    fetched = await repo.get(user_a, account.id)
    assert fetched.name == "HDFC Savings"


async def test_list_never_returns_another_users_documents(db) -> None:  # noqa: ANN001
    repo = AccountRepository(db)
    user_a, user_b = ObjectId(), ObjectId()

    await repo.insert(Account(user_id=user_a, name="A1", type=AccountType.BANK))
    await repo.insert(Account(user_id=user_a, name="A2", type=AccountType.CASH))
    await repo.insert(Account(user_id=user_b, name="B1", type=AccountType.BANK))

    a_accounts = await repo.find(user_a)
    assert {a.name for a in a_accounts} == {"A1", "A2"}
