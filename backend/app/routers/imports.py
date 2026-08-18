from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter, File, Form, UploadFile

from app.deps import CurrentUser, DbDep, SettingsDep
from app.errors import NotFoundError, ValidationProblem
from app.models.import_job import Import, ImportStatus
from app.models.job import Job, JobType
from app.parsers.pdf_parser import PdfParseError, decrypt_pdf_bytes_if_protected
from app.repositories.accounts import AccountRepository
from app.repositories.imports import ImportRepository
from app.repositories.jobs import JobRepository
from app.schemas.imports import ImportCreatedResponse, MappingSubmitRequest
from app.services import import_service

router = APIRouter(prefix="/imports", tags=["imports"])

_MAGIC_BYTES = {
    b"%PDF": "pdf",
    b"PK\x03\x04": "xlsx",  # xlsx/zip
}


def _sniff_mime(content: bytes, filename: str) -> str:
    for magic, kind in _MAGIC_BYTES.items():
        if content.startswith(magic):
            return kind
    if filename.lower().endswith(".csv"):
        return "csv"
    return "unknown"


@router.post("", response_model=ImportCreatedResponse, status_code=202)
async def create_import(
    user: CurrentUser,
    db: DbDep,
    settings: SettingsDep,
    file: UploadFile = File(...),
    account_id: str = Form(...),
    password: str | None = Form(default=None),
):
    account = await AccountRepository(db).get(user.id, ObjectId(account_id))
    if account is None:
        raise ValidationProblem("Invalid account", [{"field": "account_id", "message": "not found"}])

    content = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise ValidationProblem(
            "File too large", [{"field": "file", "message": f"exceeds {settings.max_upload_mb} MB limit"}]
        )

    kind = _sniff_mime(content, file.filename or "")
    if kind == "unknown" and not (file.filename or "").lower().endswith((".csv", ".xls", ".xlsx", ".pdf")):
        raise ValidationProblem("Unsupported file type", [{"field": "file", "message": "must be CSV, XLS/XLSX or PDF"}])

    if kind == "pdf" or (file.filename or "").lower().endswith(".pdf"):
        try:
            content = decrypt_pdf_bytes_if_protected(content, password)
        except PdfParseError as exc:
            raise ValidationProblem("Could not open PDF", [{"field": "password", "message": str(exc)}]) from exc
    # `password` (the local variable) is never referenced again and is
    # never written to the import document, a job payload, or a log (FR-2.4).

    import_doc = await import_service.create_import(
        db,
        user_id=user.id,
        account_id=account.id,
        filename=file.filename or "statement",
        mime=file.content_type or kind,
        content=content,
    )
    stored_path, sha256 = await import_service.save_upload(settings, user.id, import_doc.id, import_doc.filename, content)
    await ImportRepository(db).update(user.id, import_doc.id, {"$set": {"stored_path": stored_path, "sha256": sha256}})

    job = Job(user_id=user.id, type=JobType.PROCESS_IMPORT, payload={"import_id": str(import_doc.id)})
    await JobRepository(db).enqueue(job)

    return ImportCreatedResponse(import_id=str(import_doc.id))


@router.get("", response_model=list[Import])
async def list_imports(user: CurrentUser, db: DbDep):
    return await ImportRepository(db).list_recent(user.id)


@router.get("/{import_id}", response_model=Import)
async def get_import(import_id: str, user: CurrentUser, db: DbDep):
    import_doc = await ImportRepository(db).get(user.id, ObjectId(import_id))
    if import_doc is None:
        raise NotFoundError("Import")
    return import_doc


@router.post("/{import_id}/mapping", response_model=Import)
async def submit_mapping(import_id: str, body: MappingSubmitRequest, user: CurrentUser, db: DbDep):
    """FR-2.6: submit column mapping, resume the job."""
    import_repo = ImportRepository(db)
    import_doc = await import_repo.get(user.id, ObjectId(import_id))
    if import_doc is None:
        raise NotFoundError("Import")
    if import_doc.status != ImportStatus.NEEDS_MAPPING:
        raise ValidationProblem("Import is not awaiting a mapping", [{"field": "status", "message": import_doc.status.value}])

    await import_repo.update(user.id, import_doc.id, {"$set": {"status": ImportStatus.QUEUED.value}})
    job = Job(
        user_id=user.id,
        type=JobType.PROCESS_IMPORT,
        payload={"import_id": import_id, "mapping": body.to_mapping().as_dict()},
    )
    await JobRepository(db).enqueue(job)
    return await import_repo.get(user.id, import_doc.id)


@router.post("/{import_id}/retry", response_model=Import)
async def retry_import(import_id: str, user: CurrentUser, db: DbDep):
    """NFR-12: failed jobs are retryable."""
    import_repo = ImportRepository(db)
    import_doc = await import_repo.get(user.id, ObjectId(import_id))
    if import_doc is None:
        raise NotFoundError("Import")
    await import_repo.update(user.id, import_doc.id, {"$set": {"status": ImportStatus.QUEUED.value, "errors": []}})
    job = Job(user_id=user.id, type=JobType.PROCESS_IMPORT, payload={"import_id": import_id})
    await JobRepository(db).enqueue(job)
    return await import_repo.get(user.id, import_doc.id)


@router.delete("/{import_id}", status_code=204)
async def delete_import(import_id: str, user: CurrentUser, db: DbDep):
    """FR-2.14: removes exactly the transactions this import created."""
    import_doc = await ImportRepository(db).get(user.id, ObjectId(import_id))
    if import_doc is None:
        raise NotFoundError("Import")
    await import_service.delete_import(db, user.id, ObjectId(import_id))
