"""Resolves which LLM provider to use for a given user (FR-4.2, FR-4.12, NFR-11).

This is the one place that decides "Gemini or Claude" — everything
downstream (`app.categorise.engine`) only sees the `LLMProvider` protocol.
Precedence for both the chosen provider and its API key:

1. The user's own `settings.llm` (per-user override, set from the Settings
   screen) — this is what makes the choice "configurable by the user".
2. The system-wide default (`LLM_PROVIDER` / `GEMINI_API_KEY` /
   `ANTHROPIC_API_KEY` env vars) — used for a fresh user who hasn't
   customised anything yet, and as the key fallback when a user has picked
   a provider but not supplied their own key for it (e.g. a self-hosted
   instance that provides one shared key).

If, after that, there is still no usable API key, categorisation degrades
to rules-only and `get_llm_provider` returns `None` — the caller must treat
`None` as "skip the LLM stage entirely", not call it (FR-4.12, NFR-11).
"""

from __future__ import annotations

from app.categorise.llm.base import LLMProvider
from app.config import LLMProviderName, Settings
from app.models.user import LLMSettings


def get_llm_provider(user_llm_settings: LLMSettings, settings: Settings) -> LLMProvider | None:
    provider_name = user_llm_settings.provider or settings.llm_provider.value

    if provider_name == LLMProviderName.NONE.value:
        return None

    if provider_name == LLMProviderName.GEMINI.value:
        api_key = user_llm_settings.gemini_api_key or settings.gemini_api_key
        if not api_key:
            return None
        from app.categorise.llm.gemini_provider import GeminiProvider

        return GeminiProvider(api_key=api_key, model=settings.gemini_model)

    if provider_name == LLMProviderName.CLAUDE.value:
        api_key = user_llm_settings.claude_api_key or settings.anthropic_api_key
        if not api_key:
            return None
        from app.categorise.llm.claude_provider import ClaudeProvider

        return ClaudeProvider(api_key=api_key, model=settings.anthropic_model)

    return None
