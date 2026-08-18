from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from uuid import uuid4

from app.config import get_settings
from app.db import assert_replica_set, close_client, ensure_indexes, get_database
from app.errors import register_error_handlers
from app.logging_conf import configure_logging
from app.routers import (
    accounts,
    advisor,
    allocations,
    auth,
    categories,
    commitments,
    dashboard,
    export,
    goals,
    imports,
    income,
    investments,
    merchants,
    networth,
    rules,
    settings as settings_router,
    transactions,
    wishlist,
)

log = structlog.get_logger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # noqa: ANN001
        request_id = request.headers.get("x-request-id", str(uuid4()))
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        structlog.contextvars.clear_contextvars()
        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    db = get_database()
    if settings.env != "test":
        await assert_replica_set(db)
    await ensure_indexes(db)
    log.info("app_startup", env=settings.env)
    yield
    await close_client()
    log.info("app_shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Finance Tracker API", version="1.0.0", lifespan=lifespan)

    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)

    api = "/api/v1"
    app.include_router(auth.router, prefix=api)
    app.include_router(accounts.router, prefix=api)
    app.include_router(imports.router, prefix=api)
    app.include_router(transactions.router, prefix=api)
    app.include_router(categories.router, prefix=api)
    app.include_router(rules.router, prefix=api)
    app.include_router(merchants.router, prefix=api)
    app.include_router(income.router, prefix=api)
    app.include_router(commitments.router, prefix=api)
    app.include_router(allocations.router, prefix=api)
    app.include_router(dashboard.router, prefix=api)
    app.include_router(goals.router, prefix=api)
    app.include_router(wishlist.router, prefix=api)
    app.include_router(investments.router, prefix=api)
    app.include_router(networth.router, prefix=api)
    app.include_router(advisor.router, prefix=api)
    app.include_router(settings_router.router, prefix=api)
    app.include_router(export.router, prefix=api)

    @app.get("/healthz", tags=["meta"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
