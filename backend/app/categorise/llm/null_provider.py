from __future__ import annotations

from app.categorise.llm.base import CategorySuggestion, LLMProvider


class NullProvider(LLMProvider):
    """Used in tests and whenever a provider object is needed but should
    never actually be called. `get_llm_provider` returns `None` (not this)
    for the "disabled" case in normal operation — see factory.py."""

    name = "none"
    model = "none"

    async def categorise_batch(
        self, merchants: list[str], allowed_categories: list[tuple[str, str]]
    ) -> list[CategorySuggestion]:
        return []
