from __future__ import annotations

from app.models.investment import Investment
from app.repositories.base import Repository


class InvestmentRepository(Repository[Investment]):
    collection_name = "investments"
    model = Investment
