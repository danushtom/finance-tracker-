from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter

from app.deps import CurrentUser, DbDep
from app.errors import NotFoundError
from app.models.commitment import Commitment
from app.models.job import Job, JobType
from app.repositories.commitments import CommitmentRepository
from app.repositories.jobs import JobRepository
from app.repositories.users import UserRepository
from app.schemas.commitments import CommitmentUpdate

router = APIRouter(prefix="/commitments", tags=["commitments"])


@router.get("", response_model=list[Commitment])
async def list_commitments(user: CurrentUser, db: DbDep, status: str | None = None):
    repo = CommitmentRepository(db)
    query = {"status": status} if status else None
    return await repo.find(user.id, query, sort=[("next_expected_date", 1)])


@router.post("/detect", status_code=202)
async def detect_commitments(user: CurrentUser, db: DbDep):
    """FR-7.1: enqueue detection; results appear as status=detected
    candidates for the user to confirm."""
    job = Job(user_id=user.id, type=JobType.DETECT_RECURRING, payload={})
    await JobRepository(db).enqueue(job)
    return {"status": "queued"}


@router.patch("/{commitment_id}", response_model=Commitment)
async def update_commitment(commitment_id: str, body: CommitmentUpdate, user: CurrentUser, db: DbDep):
    """Confirm, cancel, or adjust a commitment (FR-7.2, FR-7.6)."""
    repo = CommitmentRepository(db)
    updates = body.model_dump(exclude_unset=True)
    if "category_id" in updates and updates["category_id"]:
        updates["category_id"] = ObjectId(updates["category_id"])
    if "status" in updates and updates["status"]:
        updates["status"] = updates["status"].value if hasattr(updates["status"], "value") else updates["status"]
    if not await repo.update(user.id, ObjectId(commitment_id), {"$set": updates}):
        raise NotFoundError("Commitment")
    await UserRepository(db).bump_data_version(user.id)
    return await repo.get(user.id, ObjectId(commitment_id))
