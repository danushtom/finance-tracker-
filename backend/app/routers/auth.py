from __future__ import annotations

import structlog
from fastapi import APIRouter, Request, Response

from app.deps import CurrentUser, DbDep, SettingsDep
from app.errors import UnauthorizedError
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.schemas.settings_out import UserSettingsOut
from app.services import auth_service

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"


def _set_refresh_cookie(response: Response, raw_refresh_token: str, settings) -> None:  # noqa: ANN001
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=raw_refresh_token,
        httponly=True,
        secure=settings.env != "development",
        samesite="lax",
        max_age=settings.jwt_refresh_ttl_days * 24 * 3600,
        path="/api/v1/auth",
    )


def _user_out(user) -> UserOut:  # noqa: ANN001
    return UserOut(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        settings=UserSettingsOut.from_model(user.settings),
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, request: Request, response: Response, db: DbDep, settings: SettingsDep):
    user = await auth_service.register(
        db,
        email=body.email,
        password=body.password,
        display_name=body.display_name,
        invite_code=body.invite_code,
        settings=settings,
    )
    access_token, raw_refresh = await auth_service.issue_tokens(
        db, user=user, settings=settings, user_agent=request.headers.get("user-agent")
    )
    _set_refresh_cookie(response, raw_refresh, settings)
    log.info("user_registered", user_id=str(user.id))
    return TokenResponse(access_token=access_token, user=_user_out(user))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, response: Response, db: DbDep, settings: SettingsDep):
    user = await auth_service.login(db, email=body.email, password=body.password)
    access_token, raw_refresh = await auth_service.issue_tokens(
        db, user=user, settings=settings, user_agent=request.headers.get("user-agent")
    )
    _set_refresh_cookie(response, raw_refresh, settings)
    log.info("user_logged_in", user_id=str(user.id))
    return TokenResponse(access_token=access_token, user=_user_out(user))


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, response: Response, db: DbDep, settings: SettingsDep):
    raw_refresh_token = request.cookies.get(REFRESH_COOKIE)
    if not raw_refresh_token:
        raise UnauthorizedError("No refresh token cookie present")
    access_token, new_raw_refresh, user = await auth_service.refresh_access_token(
        db,
        raw_refresh_token=raw_refresh_token,
        settings=settings,
        user_agent=request.headers.get("user-agent"),
    )
    _set_refresh_cookie(response, new_raw_refresh, settings)
    return TokenResponse(access_token=access_token, user=_user_out(user))


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response, db: DbDep):
    raw_refresh_token = request.cookies.get(REFRESH_COOKIE)
    if raw_refresh_token:
        await auth_service.logout(db, raw_refresh_token=raw_refresh_token)
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth")


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return _user_out(user)


@router.post("/change-password", status_code=204)
async def change_password(body: ChangePasswordRequest, user: CurrentUser, db: DbDep):
    await auth_service.change_password(
        db, user=user, current_password=body.current_password, new_password=body.new_password
    )


@router.delete("/me", status_code=204)
async def delete_me(user: CurrentUser, db: DbDep):
    await auth_service.delete_account(db, user_id=user.id)
