from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.models.category import CategoryClass


class CategoryCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    parent_id: str | None = None
    class_: CategoryClass = Field(alias="class")
    colour: str | None = None
    icon: str | None = None


class CategoryUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = None
    class_: CategoryClass | None = Field(default=None, alias="class")
    colour: str | None = None
    icon: str | None = None
    archived: bool | None = None
    sort_order: int | None = None


class CategoryMerge(BaseModel):
    into_id: str
