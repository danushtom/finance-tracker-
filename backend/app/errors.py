"""RFC 9457 problem+json error handling (see TECHNICAL_DESIGN.md section 10)."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ProblemError(Exception):
    """Base application error → RFC 9457 problem+json response."""

    def __init__(
        self,
        *,
        status_code: int,
        title: str,
        detail: str | None = None,
        type_: str = "about:blank",
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        self.status_code = status_code
        self.title = title
        self.detail = detail
        self.type_ = type_
        self.errors = errors
        super().__init__(detail or title)


class NotFoundError(ProblemError):
    def __init__(self, resource: str = "Resource", detail: str | None = None) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            title=f"{resource} not found",
            detail=detail,
            type_="/errors/not-found",
        )


class ConflictError(ProblemError):
    def __init__(self, title: str, detail: str | None = None) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            title=title,
            detail=detail,
            type_="/errors/conflict",
        )


class UnauthorizedError(ProblemError):
    def __init__(self, detail: str = "Authentication required") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Unauthorized",
            detail=detail,
            type_="/errors/unauthorized",
        )


class ForbiddenError(ProblemError):
    def __init__(self, detail: str = "Not allowed") -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            title="Forbidden",
            detail=detail,
            type_="/errors/forbidden",
        )


class ValidationProblem(ProblemError):
    def __init__(self, title: str, errors: list[dict[str, Any]]) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title=title,
            type_="/errors/validation",
            errors=errors,
        )


def _problem_response(request: Request, *, status_code: int, title: str,
                       detail: str | None = None, type_: str = "about:blank",
                       errors: list[dict[str, Any]] | None = None) -> JSONResponse:
    body: dict[str, Any] = {
        "type": type_,
        "title": title,
        "status": status_code,
        "instance": str(request.url.path),
    }
    if detail:
        body["detail"] = detail
    if errors:
        body["errors"] = errors
    return JSONResponse(status_code=status_code, content=body, media_type="application/problem+json")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ProblemError)
    async def _problem_handler(request: Request, exc: ProblemError) -> JSONResponse:
        return _problem_response(
            request,
            status_code=exc.status_code,
            title=exc.title,
            detail=exc.detail,
            type_=exc.type_,
            errors=exc.errors,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"field": ".".join(str(p) for p in e["loc"]), "message": e["msg"]}
            for e in exc.errors()
        ]
        return _problem_response(
            request,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Validation failed",
            type_="/errors/validation",
            errors=errors,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _problem_response(
            request,
            status_code=exc.status_code,
            title=str(exc.detail) if exc.detail else "Error",
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        import structlog

        structlog.get_logger(__name__).error("unhandled_exception", exc_info=exc)
        return _problem_response(
            request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            title="Internal server error",
        )
