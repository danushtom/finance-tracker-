from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from app.models.commitment import CommitmentStatus
from app.models.common import Minor


class CommitmentUpdate(BaseModel):
    status: CommitmentStatus | None = None  # confirm / cancel (FR-7.2, FR-7.6)
    display_name: str | None = None
    expected_amount_minor: Minor | None = None
    day_of_month: int | None = None
    next_expected_date: date | None = None
    category_id: str | None = None
