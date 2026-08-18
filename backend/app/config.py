"""Application configuration. Secrets come only from the environment (NFR-8).

Nothing here has a usable default for a secret — startup fails loudly instead
of silently running insecurely (see `Settings.validate_secrets`).
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProviderName(StrEnum):
    """The set of LLM providers the categoriser can be configured to use.

    This is a system-wide *default*; each user may independently choose
    their own provider (and supply their own API key) in Settings, see
    `app.models.user.LLMSettings`.
    """

    GEMINI = "gemini"
    CLAUDE = "claude"
    NONE = "none"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "development"
    log_level: str = "INFO"
    tz: str = "Asia/Kolkata"

    # Database
    mongodb_uri: str = "mongodb://localhost:27017/?replicaSet=rs0"
    mongodb_db: str = "finance_tracker"

    # Auth
    jwt_secret: str = ""
    jwt_access_ttl_min: int = 15
    jwt_refresh_ttl_days: int = 30
    registration_invite_code: str = ""

    # Storage
    storage_dir: str = "./storage/uploads"
    max_upload_mb: int = 20
    max_upload_rows: int = 20_000

    # LLM (FR-4, NFR-10, NFR-11) — system-wide defaults, overridable per user.
    llm_provider: LLMProviderName = LLMProviderName.GEMINI
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"
    llm_monthly_call_cap: int = 500

    # OCR
    ocr_enabled: bool = False

    # Web / CORS
    cors_origins: str = "http://localhost:3000"

    @field_validator("cors_origins")
    @classmethod
    def _split_origins(cls, v: str) -> str:
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def validate_secrets(self) -> "Settings":
        if self.env != "test" and not self.jwt_secret:
            raise RuntimeError(
                "JWT_SECRET is required and has no default. Set it in your .env file."
            )
        if self.env != "test" and self.jwt_secret in {"changeme", "secret", "default"}:
            raise RuntimeError("JWT_SECRET must not be a placeholder value.")
        return self

    def llm_key_for(self, provider: LLMProviderName) -> str:
        return {
            LLMProviderName.GEMINI: self.gemini_api_key,
            LLMProviderName.CLAUDE: self.anthropic_api_key,
            LLMProviderName.NONE: "",
        }[provider]


@lru_cache
def get_settings() -> Settings:
    return Settings()
