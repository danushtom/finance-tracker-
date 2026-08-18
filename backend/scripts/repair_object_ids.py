"""Repair documents whose ObjectId fields were persisted as strings.

Why this exists
---------------
An earlier revision of `app/models/common.py` annotated `PyObjectId` with a
`PlainSerializer` that ran in *every* mode. Repository writes build their
BSON with `model_dump(mode="python")`, so that serializer stringified
`_id` / `user_id` / every `*_id` reference on the way into Mongo.

The failure mode was silent and confusing: `/auth/login` kept working
(it queries by `email`, a string), while every authenticated request
returned 401, because `get_by_id` looks the user up by a real `ObjectId`
and matched nothing.

The serializer is now `when_used="json"`, so new writes are correct. This
script fixes documents written before that fix.

Usage
-----
    python scripts/repair_object_ids.py --dry-run    # report only
    python scripts/repair_object_ids.py              # apply

Idempotent: documents already holding real ObjectIds are left untouched,
so re-running is a no-op.
"""

from __future__ import annotations

import argparse
import asyncio
import os
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

COLLECTIONS = [
    "users",
    "refresh_tokens",
    "accounts",
    "categories",
    "merchants",
    "rules",
    "imports",
    "transactions",
    "income_sources",
    "commitments",
    "goals",
    "wishlist_items",
    "investments",
    "net_worth_snapshots",
    "llm_cache",
    "jobs",
    "derived_cache",
    "allocations",
]


def _looks_like_id_field(key: str) -> bool:
    return key == "_id" or key.endswith("_id")


def convert(value: Any, key: str | None = None) -> tuple[Any, int]:
    """Recursively convert string ObjectIds back to real ObjectIds.

    Only touches keys named `_id` or ending in `_id`, and only when the
    string actually parses as an ObjectId — so a legitimately-string field
    is never mangled. Returns (converted_value, number_of_conversions).
    """
    if isinstance(value, dict):
        changed = 0
        out = {}
        for k, v in value.items():
            out[k], n = convert(v, k)
            changed += n
        return out, changed

    if isinstance(value, list):
        changed = 0
        out_list = []
        for item in value:
            converted, n = convert(item, key)
            out_list.append(converted)
            changed += n
        return out_list, changed

    if key and _looks_like_id_field(key) and isinstance(value, str) and ObjectId.is_valid(value):
        return ObjectId(value), 1

    return value, 0


async def repair(db, *, dry_run: bool) -> None:  # noqa: ANN001
    grand_total = 0

    for name in COLLECTIONS:
        collection = db[name]
        docs_changed = 0
        fields_changed = 0

        async for doc in collection.find({}):
            repaired, n = convert(doc)
            if n == 0:
                continue

            docs_changed += 1
            fields_changed += n

            if dry_run:
                continue

            # `_id` is immutable, so a document whose own `_id` changed type
            # has to be reinserted under the corrected id rather than updated.
            if repaired["_id"] != doc["_id"] or not isinstance(doc["_id"], ObjectId):
                await collection.delete_one({"_id": doc["_id"]})
                await collection.insert_one(repaired)
            else:
                await collection.replace_one({"_id": doc["_id"]}, repaired)

        if docs_changed:
            verb = "would fix" if dry_run else "fixed"
            print(f"  {name:22} {verb} {docs_changed} doc(s), {fields_changed} field(s)")
            grand_total += fields_changed

    if grand_total == 0:
        print("  nothing to repair — all id fields already stored as ObjectId")
    elif dry_run:
        print(f"\nDRY RUN: {grand_total} field(s) would be converted. Re-run without --dry-run to apply.")
    else:
        print(f"\nDone: {grand_total} field(s) converted.")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="report what would change, write nothing")
    parser.add_argument(
        "--uri",
        default=os.environ.get("MONGODB_URI", "mongodb://localhost:27017/?replicaSet=rs0"),
    )
    parser.add_argument("--db", default=os.environ.get("MONGODB_DB", "finance_tracker"))
    args = parser.parse_args()

    print(f"Repairing {args.db} at {args.uri}")
    client = AsyncIOMotorClient(args.uri, tz_aware=True)
    try:
        await repair(client[args.db], dry_run=args.dry_run)
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
