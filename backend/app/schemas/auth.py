from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.schemas.settings_out import UserSettingsOut


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10)
    display_name: str = ""
    invite_code: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10)


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str
    settings: UserSettingsOut


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
