"""Regression tests for the BSON encoding of documents (section 5.1).

These guard a bug class that is invisible at the HTTP layer and only shows
up as mysterious 401s: if `PyObjectId` serialises to `str` in *python*
mode, every repository write stores `_id`/`user_id` as strings, reads by
`ObjectId` match nothing, and login (which queries by email) keeps working
while every authenticated request fails.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from bson import ObjectId

from app.models.account import Account, AccountType
from app.models.transaction import Transaction


def test_object_ids_stay_object_ids_in_python_mode() -> None:
    """`mode="python"` is what repositories hand to Motor — it must
    produce real ObjectIds, never strings."""
    user_id = ObjectId()
    account = Account(user_id=user_id, name="HDFC Savings", type=AccountType.BANK)

    doc = account.model_dump(by_alias=True, mode="python")

    assert isinstance(doc["_id"], ObjectId), f"_id became {type(doc['_id']).__name__}"
    assert isinstance(doc["user_id"], ObjectId), f"user_id became {type(doc['user_id']).__name__}"
    assert doc["user_id"] == user_id


def test_object_ids_render_as_strings_in_json_mode() -> None:
    """API responses still need the string form."""
    user_id = ObjectId()
    account = Account(user_id=user_id, name="HDFC Savings", type=AccountType.BANK)

    doc = account.model_dump(by_alias=True, mode="json")

    assert doc["user_id"] == str(user_id)
    assert isinstance(doc["user_id"], str)


def test_optional_object_id_fields_survive_python_mode() -> None:
    txn = Transaction(
        user_id=ObjectId(),
        account_id=ObjectId(),
        import_id=ObjectId(),
        category_id=ObjectId(),
        date=date(2026, 8, 18),
        description_raw="UPI/DR/451233098711/SWIGGY/HDFC",
        merchant_norm="SWIGGY HDFC",
        amount_minor=-50_000,
        direction="debit",
        kind="expense",
        fingerprint="abc123",
    )

    doc = txn.model_dump(by_alias=True, mode="python")

    for field in ("_id", "user_id", "account_id", "import_id", "category_id"):
        assert isinstance(doc[field], ObjectId), f"{field} became {type(doc[field]).__name__}"


def test_dates_encode_as_datetime_for_bson() -> None:
    """BSON has no date-only type; a bare `datetime.date` fails to encode,
    so MongoDate fields must come out as UTC-midnight datetimes."""
    txn = Transaction(
        user_id=ObjectId(),
        account_id=ObjectId(),
        date=date(2026, 8, 18),
        description_raw="x",
        merchant_norm="X",
        amount_minor=-1,
        direction="debit",
        kind="expense",
        fingerprint="fp",
    )

    doc = txn.model_dump(by_alias=True, mode="python")

    assert isinstance(doc["date"], datetime)
    assert doc["date"] == datetime(2026, 8, 18, tzinfo=UTC)
