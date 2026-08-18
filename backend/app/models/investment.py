from __future__ import annotations

from app.models.common import Minor, MongoDate, UserScopedModel


class Investment(UserScopedModel):
    name: str
    type: str  # index_fund|active_fund|debt|stock|gold|fd|epf_ppf|other
    invested_minor: Minor
    current_value_minor: Minor
    units: float | None = None
    identifier: str | None = None  # AMFI scheme code / ticker (FR-14.6 hook)
    value_as_of: MongoDate | None = None
    notes: str | None = None
    archived: bool = False
