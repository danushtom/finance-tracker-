from __future__ import annotations

from enum import StrEnum

from pydantic import ConfigDict, Field

from app.models.common import PyObjectId, UserScopedModel


class CategoryClass(StrEnum):
    """Drives every calculation — not the category name (ADR-3, FR-5.2)."""

    FIXED = "fixed"
    VARIABLE = "variable"
    ISOLATED = "isolated"
    INCOME = "income"
    TRANSFER = "transfer"
    INVESTMENT = "investment"


class Category(UserScopedModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    name: str
    parent_id: PyObjectId | None = None
    # `class` is a Python keyword, so the attribute is `class_` but the wire
    # / Mongo field is `class` — this is the field that drives all Safe-to-
    # Spend maths, never the category name (ADR-3, FR-5.2).
    class_: CategoryClass = Field(default=CategoryClass.VARIABLE, alias="class")
    colour: str | None = None
    icon: str | None = None
    is_system: bool = False
    archived: bool = False
    sort_order: int = 0
