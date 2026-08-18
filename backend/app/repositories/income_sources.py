from __future__ import annotations

from app.models.income import IncomeSource
from app.repositories.base import Repository


class IncomeSourceRepository(Repository[IncomeSource]):
    collection_name = "income_sources"
    model = IncomeSource
