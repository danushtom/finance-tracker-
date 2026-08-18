"""`LLMProvider` abstraction (ADR-1, ADR-6; requirement: "keep it dynamic
between Gemini and Claude, configurable by the user").

The categoriser code (`app.categorise.engine`) never imports a specific
vendor SDK. It depends only on this `Protocol`, so the provider can be
swapped — or disabled entirely — per user without touching the pipeline.
Every implementation must uphold the same contract:

- Input is a batch of already-sanitised (NFR-10) merchant strings only.
- `temperature = 0`, deterministic-as-possible, JSON-only output.
- A merchant not in `allowed_category_ids` in the response is treated by
  the caller as `Uncategorised` — providers should not need to enforce
  this themselves, but should try to only return ids they were given.
- Providers must not raise on individual bad merchants; they should omit
  them from the result so the rest of the batch still succeeds.
- Timeouts and retries are the provider's responsibility internally; if it
  ultimately cannot answer, it raises `LLMUnavailableError` and the caller
  degrades the whole batch to `Uncategorised` (FR-4.12).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class LLMUnavailableError(Exception):
    pass


@dataclass
class CategorySuggestion:
    merchant: str
    category_id: str  # the string id from `allowed_categories`, or "uncategorised"
    confidence: int  # 0-100


class LLMProvider(Protocol):
    name: str
    model: str

    async def categorise_batch(
        self,
        merchants: list[str],
        allowed_categories: list[tuple[str, str]],  # (id, name)
    ) -> list[CategorySuggestion]:
        """Classify a batch of normalised merchant strings (already
        sanitised by the caller) against the user's allowed category list.
        Raises `LLMUnavailableError` if the provider could not respond
        after its internal retries."""
        ...
