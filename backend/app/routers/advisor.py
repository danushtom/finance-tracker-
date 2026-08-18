from __future__ import annotations

from datetime import date

from fastapi import APIRouter

from app.deps import CurrentUser, DbDep
from app.services.advisor import build_summary, detect_anomalies

router = APIRouter(prefix="/advisor", tags=["advisor"])


@router.get("/summary")
async def get_summary(user: CurrentUser, db: DbDep):
    summary = await build_summary(db, user)
    return summary


@router.get("/anomalies")
async def get_anomalies(user: CurrentUser, db: DbDep):
    anomalies = await detect_anomalies(db, user)
    return {"anomalies": anomalies}
