"""Single worker process polling `jobs` (section 12).

Lease-based locking makes a crashed worker's job reclaimable —
`lease_next` only picks up jobs that are queued or whose lease has expired.
`attempts > max_attempts` moves a job to `failed`, surfaced in the UI with a
retry action (NFR-12).

Chosen over Celery/ARQ specifically to avoid a Redis dependency and keep
`docker compose up` sufficient (ADR-4).
"""

from __future__ import annotations

import asyncio
import os
import socket
from datetime import timedelta

import structlog

from app.config import get_settings
from app.db import assert_replica_set, close_client, ensure_indexes, get_database
from app.logging_conf import configure_logging
from app.repositories.jobs import JobRepository
from app.worker.handlers import HANDLERS

log = structlog.get_logger(__name__)

POLL_INTERVAL_S = 2
LEASE = timedelta(minutes=5)
WORKER_ID = f"{socket.gethostname()}-{os.getpid()}"


async def run_forever() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    db = get_database()
    await assert_replica_set(db)
    await ensure_indexes(db)
    job_repo = JobRepository(db)

    log.info("worker_started", worker_id=WORKER_ID)
    try:
        while True:
            job = await job_repo.lease_next(WORKER_ID, LEASE)
            if job is None:
                await asyncio.sleep(POLL_INTERVAL_S)
                continue

            handler = HANDLERS.get(job.type.value)
            if handler is None:
                await job_repo.mark_failed(job, f"no handler for job type {job.type.value}")
                continue

            log.info("job_started", job_id=str(job.id), type=job.type.value, attempt=job.attempts)
            try:
                await handler(db, settings, job)
                await job_repo.mark_done(job.id)
                log.info("job_done", job_id=str(job.id), type=job.type.value)
            except Exception as exc:  # noqa: BLE001 - a bad job must not kill the worker loop
                log.error("job_failed", job_id=str(job.id), type=job.type.value, error=str(exc))
                await job_repo.mark_failed(job, str(exc))
    finally:
        await close_client()


if __name__ == "__main__":
    asyncio.run(run_forever())
