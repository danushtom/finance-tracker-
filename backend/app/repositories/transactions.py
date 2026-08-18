"""Transaction repository — the core collection.

Includes the aggregation helpers that back Safe-to-Spend (FR-8.3) and the
dashboard category breakdown (section 9.2), so those pipelines are written
once and unit-testable independently of the HTTP layer.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from bson import ObjectId
from pymongo.errors import BulkWriteError

from app.models.common import Minor
from app.models.transaction import Transaction
from app.repositories.base import Repository


class TransactionRepository(Repository[Transaction]):
    collection_name = "transactions"
    model = Transaction

    async def insert_many_dedup(self, txns: list[Transaction]) -> tuple[int, int]:
        """Bulk insert with `ordered=False`; duplicates are detected by the
        unique `{user_id, fingerprint}` index, not an application check
        (FR-2.11, ADR-8). Returns (inserted, duplicates_skipped)."""
        if not txns:
            return 0, 0
        docs = [t.model_dump(by_alias=True, mode="python") for t in txns]
        try:
            result = await self.col.insert_many(docs, ordered=False)
            return len(result.inserted_ids), 0
        except BulkWriteError as exc:
            write_errors = exc.details.get("writeErrors", [])
            dup_count = sum(1 for e in write_errors if e.get("code") == 11000)
            other = [e for e in write_errors if e.get("code") != 11000]
            if other:
                raise
            inserted = len(docs) - len(write_errors)
            return inserted, dup_count

    async def list_filtered(
        self,
        user_id: ObjectId,
        *,
        month: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        account_id: ObjectId | None = None,
        category_id: ObjectId | None = None,
        category_class: str | None = None,
        kind: str | None = None,
        needs_review: bool | None = None,
        min_minor: int | None = None,
        max_minor: int | None = None,
        q: str | None = None,
        cursor_id: ObjectId | None = None,
        limit: int = 100,
    ) -> list[Transaction]:
        query: dict[str, Any] = {}
        if month:
            start, end = _month_bounds(month)
            query["date"] = {"$gte": start, "$lt": end}
        if date_from or date_to:
            date_q: dict[str, Any] = {}
            if date_from:
                date_q["$gte"] = date_from
            if date_to:
                date_q["$lte"] = date_to
            query["date"] = {**query.get("date", {}), **date_q}
        if account_id:
            query["account_id"] = account_id
        if category_id:
            query["category_id"] = category_id
        if category_class:
            query["category_class"] = category_class
        if kind:
            query["kind"] = kind
        if needs_review is not None:
            query["needs_review"] = needs_review
        if min_minor is not None or max_minor is not None:
            amt: dict[str, Any] = {}
            if min_minor is not None:
                amt["$gte"] = min_minor
            if max_minor is not None:
                amt["$lte"] = max_minor
            query["amount_minor"] = amt
        if q:
            query["$text"] = {"$search": q}
        if cursor_id:
            query["_id"] = {"$lt": cursor_id}
        return await self.find(user_id, query, sort=[("date", -1), ("_id", -1)], limit=min(limit, 200))

    async def sum_outflows(
        self,
        user_id: ObjectId,
        month: str,
        *,
        class_in: list[str] | None = None,
        class_: str | None = None,
        up_to: date | None = None,
    ) -> Minor:
        start, end = _month_bounds(month)
        if up_to:
            end = min(end, up_to)
        match: dict[str, Any] = {
            "user_id": user_id,
            "date": {"$gte": start, "$lt": end},
            "kind": {"$in": ["expense", "refund"]},
        }
        if class_in:
            match["category_class"] = {"$in": class_in}
        elif class_:
            match["category_class"] = class_
        pipeline = [{"$match": match}, {"$group": {"_id": None, "total": {"$sum": "$amount_minor"}}}]
        result = [d async for d in self.col.aggregate(pipeline)]
        return abs(int(result[0]["total"])) if result else 0

    async def sum_income(
        self, user_id: ObjectId, month: str, *, income_type: str | None = None
    ) -> Minor:
        start, end = _month_bounds(month)
        match: dict[str, Any] = {
            "user_id": user_id,
            "date": {"$gte": start, "$lt": end},
            "kind": "income",
            "direction": "credit",
        }
        pipeline: list[dict[str, Any]] = [{"$match": match}]
        if income_type:
            pipeline += [
                {
                    "$lookup": {
                        "from": "income_sources",
                        "localField": "income_source_id",
                        "foreignField": "_id",
                        "as": "src",
                    }
                },
                {"$match": {"src.type": income_type}},
            ]
        pipeline.append({"$group": {"_id": None, "total": {"$sum": "$amount_minor"}}})
        result = [d async for d in self.col.aggregate(pipeline)]
        return int(result[0]["total"]) if result else 0

    async def category_breakdown(self, user_id: ObjectId, month: str) -> list[dict[str, Any]]:
        start, end = _month_bounds(month)
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "date": {"$gte": start, "$lt": end},
                    "kind": {"$in": ["expense", "refund"]},
                }
            },
            {
                "$group": {
                    "_id": {"cls": "$category_class", "cat": "$category_id"},
                    "total": {"$sum": "$amount_minor"},
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"total": 1}},
        ]
        return [d async for d in self.col.aggregate(pipeline)]

    async def merchant_history(
        self, user_id: ObjectId, merchant_norm: str, *, months_back: int = 12
    ) -> list[Transaction]:
        return await self.find(
            user_id, {"merchant_norm": merchant_norm, "direction": "debit"}, sort=[("date", 1)]
        )

    async def delete_by_import(self, user_id: ObjectId, import_id: ObjectId, *, session: Any = None) -> int:
        result = await self.col.delete_many(
            self._scoped(user_id, {"import_id": import_id}), session=session
        )
        return result.deleted_count

    async def bulk_set_category(
        self, user_id: ObjectId, transaction_ids: list[ObjectId], category_id: ObjectId
    ) -> int:
        result = await self.col.update_many(
            self._scoped(user_id, {"_id": {"$in": transaction_ids}}),
            {
                "$set": {
                    "category_id": category_id,
                    "categorised_by": "user",
                    "confidence": 100,
                    "needs_review": False,
                }
            },
        )
        return result.modified_count

    async def recategorise_matching(
        self, user_id: ObjectId, match_query: dict[str, Any], category_id: ObjectId
    ) -> int:
        """Used by rule backfill (FR-4.8). Never touches user-set categories
        (FR-4.7)."""
        query = self._scoped(user_id, {**match_query, "categorised_by": {"$ne": "user"}})
        result = await self.col.update_many(
            query,
            {
                "$set": {
                    "category_id": category_id,
                    "categorised_by": "rule",
                    "confidence": 95,
                    "needs_review": False,
                }
            },
        )
        return result.modified_count

    async def count_matching(self, user_id: ObjectId, match_query: dict[str, Any]) -> int:
        query = self._scoped(user_id, {**match_query, "categorised_by": {"$ne": "user"}})
        return await self.col.count_documents(query)


def _month_bounds(month: str) -> tuple[date, date]:
    year, mon = int(month[:4]), int(month[5:7])
    start = date(year, mon, 1)
    end = date(year + 1, 1, 1) if mon == 12 else date(year, mon + 1, 1)
    return start, end
