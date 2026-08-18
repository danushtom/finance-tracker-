"""Seeds a brand-new user with the default category taxonomy (FR-5.3) and
the seed rule pack (FR-4.11). Categories/rules are user-scoped documents,
so this runs once at registration rather than at API startup."""

from __future__ import annotations

from pathlib import Path

import yaml
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.category import Category, CategoryClass
from app.models.rule import MatchType, Rule, RuleSource
from app.repositories.categories import CategoryRepository
from app.repositories.rules import RuleRepository

_DATA_DIR = Path(__file__).resolve().parent.parent / "categorise"


async def seed_new_user(db: AsyncIOMotorDatabase, user_id: ObjectId) -> None:
    category_repo = CategoryRepository(db)
    rule_repo = RuleRepository(db)

    taxonomy = yaml.safe_load((_DATA_DIR / "seed_categories.yaml").read_text())

    name_to_id: dict[str, ObjectId] = {}
    subname_to_id: dict[tuple[str, str], ObjectId] = {}

    for sort_order, entry in enumerate(taxonomy):
        parent = Category(
            user_id=user_id,
            name=entry["name"],
            class_=CategoryClass(entry["class"]),
            is_system=True,
            sort_order=sort_order,
        )
        await category_repo.insert(parent)
        name_to_id[entry["name"]] = parent.id

        for sub_order, sub_name in enumerate(entry.get("subcategories", [])):
            child = Category(
                user_id=user_id,
                name=sub_name,
                parent_id=parent.id,
                class_=CategoryClass(entry["class"]),
                is_system=True,
                sort_order=sub_order,
            )
            await category_repo.insert(child)
            subname_to_id[(entry["name"], sub_name)] = child.id

    seed_rules = yaml.safe_load((_DATA_DIR / "seed_rules.yaml").read_text())
    for priority, entry in enumerate(reversed(seed_rules)):
        category_name = entry["category"]
        subcategory_name = entry.get("subcategory")
        category_id = name_to_id.get(category_name)
        if category_id is None:
            continue
        subcategory_id = subname_to_id.get((category_name, subcategory_name)) if subcategory_name else None
        rule = Rule(
            user_id=user_id,
            match_type=MatchType(entry["match_type"]),
            pattern=entry["pattern"].upper(),
            category_id=category_id,
            subcategory_id=subcategory_id,
            priority=100 + priority,
            source=RuleSource.SEED,
        )
        await rule_repo.insert(rule)
