from __future__ import annotations

import asyncio

import structlog

from app.categorise.llm.base import CategorySuggestion, LLMProvider, LLMUnavailableError
from app.categorise.llm.prompt import build_prompt, parse_response

log = structlog.get_logger(__name__)

_TIMEOUT_S = 30
_MAX_RETRIES = 2


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        self.model = model
        try:
            from google import genai
        except ImportError as exc:  # pragma: no cover - dependency always declared
            raise LLMUnavailableError("google-genai package is not installed") from exc
        self._client = genai.Client(api_key=api_key)

    async def categorise_batch(
        self, merchants: list[str], allowed_categories: list[tuple[str, str]]
    ) -> list[CategorySuggestion]:
        if not merchants:
            return []
        prompt = build_prompt(merchants, allowed_categories)

        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=0,
            max_output_tokens=2048,
            response_mime_type="application/json",
        )

        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = await asyncio.wait_for(
                    self._client.aio.models.generate_content(
                        model=self.model, contents=prompt, config=config
                    ),
                    timeout=_TIMEOUT_S,
                )
                text = response.text or "[]"
                items = parse_response(text)
                return _to_suggestions(items)
            except Exception as exc:  # noqa: BLE001 - broad: any provider failure should retry/degrade
                last_error = exc
                log.warning("gemini_categorise_attempt_failed", attempt=attempt, error=str(exc))
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(2**attempt)
        raise LLMUnavailableError(f"Gemini categorisation failed after retries: {last_error}")


def _to_suggestions(items: list[dict]) -> list[CategorySuggestion]:
    out = []
    for item in items:
        try:
            out.append(
                CategorySuggestion(
                    merchant=str(item["merchant"]),
                    category_id=str(item.get("category_id", "uncategorised")),
                    confidence=int(item.get("confidence", 0)),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return out
