from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from app.models.common import Minor, PyObjectId, UserScopedModel


class ImportStatus(StrEnum):
    QUEUED = "queued"
    PARSING = "parsing"
    NEEDS_MAPPING = "needs_mapping"
    CATEGORISING = "categorising"
    NEEDS_REVIEW = "needs_review"
    COMPLETED = "completed"
    FAILED = "failed"


class ImportSummary(BaseModel):
    rows_found: int = 0
    imported: int = 0
    duplicates_skipped: int = 0
    failed: int = 0
    date_from: date | None = None
    date_to: date | None = None
    opening_balance_minor: Minor | None = None
    closing_balance_minor: Minor | None = None
    llm_calls: int = 0
    needs_review_count: int = 0


class ImportError(BaseModel):
    row: int
    reason: str


class Import(UserScopedModel):
    account_id: PyObjectId
    filename: str
    stored_path: str
    mime: str
    size_bytes: int
    sha256: str
    status: ImportStatus = ImportStatus.QUEUED
    parser: str | None = None  # "csv" | "xlsx" | "pdf" | "pdf_ocr"
    summary: ImportSummary = ImportSummary()
    errors: list[ImportError] = []
    preview: list[dict[str, Any]] = []
    started_at: datetime | None = None
    finished_at: datetime | None = None
