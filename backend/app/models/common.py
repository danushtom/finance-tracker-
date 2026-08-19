"""Shared Mongo document conventions (TECHNICAL_DESIGN.md section 5.1).

- Every collection except `users` carries `user_id` as the first field of
  every index (NFR-7).
- Every document has `created_at` / `updated_at` (UTC).
- Money is stored as integer minor units (paise) in fields suffixed
  `_minor` (NFR-5) — the `Minor` type alias documents that convention at
  the type level so a reviewer immediately sees which fields are money.
- `schema_version` allows forward migration (section 16).
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated, Any

from bson import ObjectId
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainSerializer,
    PlainValidator,
    WithJsonSchema,
)

# Minor currency units (paise). Never a float anywhere in the stack (NFR-5).
Minor = int


def _validate_object_id(v: Any) -> ObjectId:
    if isinstance(v, ObjectId):
        return v
    if isinstance(v, str) and ObjectId.is_valid(v):
        return ObjectId(v)
    raise ValueError(f"Invalid ObjectId: {v!r}")


# `ObjectId` is not a type pydantic knows how to build a core schema for.
# `PlainValidator` (unlike `BeforeValidator`) replaces schema generation
# entirely, so this works on a bare `BaseModel` too — not just on
# `MongoModel`, which sets `arbitrary_types_allowed=True`. `WithJsonSchema`
# gives it a sane OpenAPI representation (a string) instead of failing
# schema generation for the docs.
#
# `when_used="json"` is load-bearing and must not be removed: repository
# writes build their BSON document with `model_dump(mode="python")`, so an
# always-on serializer would stringify every `_id`/`user_id` on the way
# INTO Mongo. Reads then look those documents up by real `ObjectId` and
# match nothing — login succeeds (it queries by email) while every
# authenticated request 401s. Python mode must yield a real `ObjectId`;
# only JSON/API output gets the string form.
PyObjectId = Annotated[
    ObjectId,
    PlainValidator(_validate_object_id),
    PlainSerializer(lambda v: str(v), return_type=str, when_used="json"),
    WithJsonSchema({"type": "string"}),
]


def _validate_mongo_date(v: Any) -> date:
    # BSON has no date-only type; Mongo always hands back a `datetime`
    # (or, before insertion, we might see an ISO string) for what is
    # conceptually a calendar date (section 5.1: "stored as UTC midnight
    # of the local calendar date"). `datetime` is a `date` subclass, so
    # the datetime check must come first.
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        return date.fromisoformat(v)
    raise ValueError(f"Invalid date: {v!r}")


def _serialize_mongo_date(v: date | None) -> datetime | None:
    if v is None:
        return None
    return datetime(v.year, v.month, v.day, tzinfo=UTC)


# A calendar date stored in Mongo as UTC midnight `datetime`, because BSON
# has no date-only type — using plain `datetime.date` here would fail to
# encode at all (NFR-16, section 5.1). Every "date" field on a document
# uses this instead of the bare `date` type.
MongoDate = Annotated[
    date,
    BeforeValidator(_validate_mongo_date),
    PlainSerializer(_serialize_mongo_date, return_type=datetime),
]


def to_utc_datetime(value: date | datetime | None) -> datetime | None:
    """Coerce a calendar date to the UTC-midnight `datetime` BSON needs.

    BSON has no date-only type, so a bare `datetime.date` fails to encode
    with `InvalidDocument`. Document *fields* handle this via `MongoDate`,
    but query filters are built as plain dicts in the repository layer and
    must call this explicitly before any `date` reaches Mongo.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime(value.year, value.month, value.day, tzinfo=UTC)


def to_bson_safe(value: Any) -> Any:
    """Recursively converts bare `datetime.date` values (BSON has no
    date-only type) to UTC-midnight `datetime`, leaving everything else
    untouched. Used by `Repository.update`/raw `$set` payloads that are
    built from request DTOs rather than a `MongoModel` (whose fields
    already serialize themselves via `MongoDate`/`PyObjectId`)."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return _serialize_mongo_date(value)
    if isinstance(value, dict):
        return {k: to_bson_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_bson_safe(v) for v in value]
    return value


def utcnow() -> datetime:
    return datetime.now(UTC)


class MongoModel(BaseModel):
    """Base for documents stored in Mongo."""

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: PyObjectId = Field(default_factory=ObjectId, alias="_id")
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    schema_version: int = 1

    def to_mongo(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, mode="python")


class UserScopedModel(MongoModel):
    user_id: PyObjectId
