from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from app.models.common import MongoModel, PyObjectId


class JobType(StrEnum):
    PROCESS_IMPORT = "process_import"
    BACKFILL_RULE = "backfill_rule"
    DETECT_RECURRING = "detect_recurring"
    SNAPSHOT_NETWORTH = "snapshot_networth"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class Job(MongoModel):
    user_id: PyObjectId
    type: JobType
    payload: dict[str, Any] = Field(default_factory=dict)
    status: JobStatus = JobStatus.QUEUED
    attempts: int = 0
    max_attempts: int = 3
    locked_by: str | None = None
    locked_at: datetime | None = None
    error: str | None = None
