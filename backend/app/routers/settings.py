"""User-editable rules (FR-11.5): savings rate, investing rate, buffer
size, variable-income split, low-confidence threshold, and per-user LLM
provider/key — the configurability the product is built around."""

from __future__ import annotations

from fastapi import APIRouter

from app.deps import CurrentUser, DbDep
from app.repositories.users import UserRepository
from app.schemas.settings import SettingsUpdate
from app.schemas.settings_out import UserSettingsOut

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=UserSettingsOut)
async def get_settings(user: CurrentUser):
    return UserSettingsOut.from_model(user.settings)


@router.patch("", response_model=UserSettingsOut)
async def update_settings(body: SettingsUpdate, user: CurrentUser, db: DbDep):
    updates = body.model_dump(exclude_unset=True, exclude_none=True)
    if not updates:
        return UserSettingsOut.from_model(user.settings)

    set_ops = {}
    for key, value in updates.items():
        if key == "llm":
            # Merge rather than replace, so omitting a key (e.g. not
            # resending an already-stored API key) doesn't wipe it.
            merged = user.settings.llm.model_dump()
            merged.update({k: v for k, v in value.items() if v is not None})
            set_ops["settings.llm"] = merged
        elif key == "variable_split":
            set_ops["settings.variable_split"] = value
        else:
            set_ops[f"settings.{key}"] = value

    user_repo = UserRepository(db)
    await user_repo.update(user.id, {"$set": set_ops})
    await user_repo.bump_data_version(user.id)

    updated = await user_repo.get_by_id(user.id)
    return UserSettingsOut.from_model(updated.settings)
