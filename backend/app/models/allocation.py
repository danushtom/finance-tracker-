"""Variable-income allocation proposals (FR-12). Not enumerated in
TECHNICAL_DESIGN.md section 5.2's collection list, but required by the API
surface in section 10.4 (`GET/PATCH /allocations`) — added here as its own
small user-scoped collection, following the same conventions as every
other collection in that section."""

from __future__ import annotations

from app.models.common import Minor, PyObjectId, UserScopedModel


class Allocation(UserScopedModel):
    transaction_id: PyObjectId  # the variable-income credit this proposal is for
    month: str  # "YYYY-MM"
    total_minor: Minor
    proposed_invest_minor: Minor
    proposed_goals_minor: Minor
    proposed_discretionary_minor: Minor
    override_invest_minor: Minor | None = None
    override_goals_minor: Minor | None = None
    override_discretionary_minor: Minor | None = None
    invest_executed_minor: Minor = 0
    goals_executed_minor: Minor = 0
