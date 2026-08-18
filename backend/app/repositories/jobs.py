"""Jobs are not user-scoped in the query sense the other repos are — the
worker polls across all users — but every job document still carries
`user_id` for provenance and payload scoping."""

from __future__ import annotations

from datetime import timedelta

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.common import utcnow
from app.models.job import Job, JobStatus


class JobRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.col = db.jobs

    async def enqueue(self, job: Job) -> Job:
        await self.col.insert_one(job.model_dump(by_alias=True, mode="python"))
        return job

    async def lease_next(self, worker_id: str, lease: timedelta) -> Job | None:
        now = utcnow()
        doc = await self.col.find_one_and_update(
            {
                "status": JobStatus.QUEUED.value,
                "$or": [{"locked_at": None}, {"locked_at": {"$lt": now - lease}}],
            },
            {
                "$set": {"status": JobStatus.RUNNING.value, "locked_by": worker_id, "locked_at": now},
                "$inc": {"attempts": 1},
            },
            sort=[("created_at", 1)],
            return_document=True,
        )
        return Job.model_validate(doc) if doc else None

    async def mark_done(self, job_id: ObjectId) -> None:
        await self.col.update_one(
            {"_id": job_id}, {"$set": {"status": JobStatus.DONE.value, "updated_at": utcnow()}}
        )

    async def mark_failed(self, job: Job, error: str) -> None:
        status = JobStatus.QUEUED if job.attempts < job.max_attempts else JobStatus.FAILED
        await self.col.update_one(
            {"_id": job.id},
            {"$set": {"status": status.value, "error": error, "updated_at": utcnow()}},
        )

    async def get(self, job_id: ObjectId) -> Job | None:
        doc = await self.col.find_one({"_id": job_id})
        return Job.model_validate(doc) if doc else None
