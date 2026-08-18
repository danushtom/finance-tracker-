"""Data portability (FR-16.2, FR-16.3): the user's data is theirs and must
be extractable in one action."""

from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime

from bson import ObjectId
from fastapi import APIRouter, Response

from app.deps import CurrentUser, DbDep
from app.repositories.accounts import AccountRepository
from app.repositories.goals import GoalRepository
from app.repositories.investments import InvestmentRepository
from app.repositories.rules import RuleRepository
from app.repositories.transactions import TransactionRepository
from app.repositories.wishlist import WishlistRepository

router = APIRouter(prefix="/export", tags=["export"])


def _json_default(o):  # noqa: ANN001, ANN202
    if isinstance(o, ObjectId):
        return str(o)
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    return str(o)


@router.get("/transactions.csv")
async def export_transactions_csv(
    user: CurrentUser,
    db: DbDep,
    date_from: date | None = None,
    date_to: date | None = None,
    category_id: str | None = None,
):
    txn_repo = TransactionRepository(db)
    txns = await txn_repo.list_filtered(
        user.id,
        date_from=date_from,
        date_to=date_to,
        category_id=ObjectId(category_id) if category_id else None,
        limit=100_000,
    )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["date", "description", "merchant", "amount_minor", "direction", "kind", "category_id", "needs_review"])
    for t in txns:
        writer.writerow(
            [t.date.isoformat(), t.description_raw, t.merchant_norm, t.amount_minor, t.direction, t.kind,
             str(t.category_id) if t.category_id else "", t.needs_review]
        )

    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=transactions.csv"},
    )


@router.get("/all.json")
async def export_all_json(user: CurrentUser, db: DbDep):
    txn_repo = TransactionRepository(db)

    bundle = {
        "exported_at": datetime.utcnow().isoformat(),
        "user": {"email": user.email, "display_name": user.display_name, "settings": user.settings.model_dump()},
        "accounts": [a.model_dump(mode="json") for a in await AccountRepository(db).find(user.id)],
        "transactions": [t.model_dump(mode="json") for t in await txn_repo.find(user.id, limit=0)],
        "rules": [r.model_dump(mode="json") for r in await RuleRepository(db).find(user.id)],
        "goals": [g.model_dump(mode="json") for g in await GoalRepository(db).find(user.id)],
        "wishlist": [w.model_dump(mode="json") for w in await WishlistRepository(db).find(user.id)],
        "investments": [i.model_dump(mode="json") for i in await InvestmentRepository(db).find(user.id)],
    }

    return Response(
        content=json.dumps(bundle, default=_json_default, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=finance-tracker-export.json"},
    )
