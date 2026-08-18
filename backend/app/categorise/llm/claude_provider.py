from __future__ import annotations

import asyncio

import structlog

from app.categorise.llm.base import CategorySuggestion, LLMProvider, LLMUnavailableError
from app.categorise.llm.prompt import build_prompt, parse_response

log = structlog.get_logger(__name__)

_TIMEOUT_S = 30
_MAX_RETRIES = 2


class ClaudeProvider(LLMProvider):
    name = "claude"

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5") -> None:
        self.model = model
        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:  # pragma: no cover - dependency always declared
            raise LLMUnavailableError("anthropic package is not installed") from exc
        self._client = AsyncAnthropic(api_key=api_key, timeout=_TIMEOUT_S)

    async def categorise_batch(
        self, merchants: list[str], allowed_categories: list[tuple[str, str]]
    ) -> list[CategorySuggestion]:
        if not merchants:
            return []
        prompt = build_prompt(merchants, allowed_categories)

        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = await self._client.messages.create(
                    model=self.model,
                    max_tokens=2048,
                    temperature=0,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = "".join(
                    block.text for block in response.content if getattr(block, "type", None) == "text"
                )
                items = parse_response(text)
                return _to_suggestions(items)
            except Exception as exc:  # noqa: BLE001 - broad: any provider failure should retry/degrade
                last_error = exc
                log.warning("claude_categorise_attempt_failed", attempt=attempt, error=str(exc))
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(2**attempt)
        raise LLMUnavailableError(f"Claude categorisation failed after retries: {last_error}")


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
