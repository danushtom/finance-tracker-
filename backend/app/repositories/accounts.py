from __future__ import annotations

from app.models.account import Account
from app.repositories.base import Repository


class AccountRepository(Repository[Account]):
    collection_name = "accounts"
    model = Account
