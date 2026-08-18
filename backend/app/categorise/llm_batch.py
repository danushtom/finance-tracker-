"""LLM fallback orchestration: batching, caching, budget guard (FR-4.2, FR-4.13).

This is the layer above the raw `LLMProvider` — it never talks to a vendor
SDK directly. It:

  1. Sanitises every merchant (NFR-10) — anything that fails is dropped to
     Uncategorised without ever reaching the network.
  2. Checks `llm_cache` first, so a merchant is classified once, ever (G-2)
     — re-uploading a statement never re-invokes the LLM for a merchant
     already cached under the current `prompt_version`.
  3. Batches the remaining unknown merchants (up to 40 per request).
  4. Enforces the per-user monthly call cap before calling out (FR-4.13);
     over-cap merchants fall through to the review queue as Uncategorised.
  5. Writes results back to `llm_cache` so future imports never re-ask.
"""

from __future__ import annotations

from datetime import date

import structlog
from bson import ObjectId

from app.categorise.llm.base import CategorySuggestion, LLMProvider, LLMUnavailableError
from app.categorise.llm.prompt import PROMPT_VERSION
from app.categorise.sanitiser import try_sanitise
from app.models.llm_cache import LLMCacheEntry
from app.repositories.llm_cache import LLMCacheRepository
from app.repositories.users import UserRepository

log = structlog.get_logger(__name__)

BATCH_SIZE = 40


async def categorise_unknown_merchants(
    *,
    user_id: ObjectId,
    merchants: list[str],
    allowed_categories: list[tuple[str, str]],  # (id, name)
    provider: LLMProvider | None,
    llm_cache_repo: LLMCacheRepository,
    user_repo: UserRepository,
    monthly_call_cap: int,
) -> dict[str, CategorySuggestion]:
    """Returns merchant_norm -> CategorySuggestion for every merchant that
    could be resolved. Merchants that fail sanitisation, exceed the budget,
    or the provider can't answer are simply absent from the result — the
    caller treats a missing entry as Uncategorised (FR-4.12)."""
    results: dict[str, CategorySuggestion] = {}
    if provider is None:
        return results

    month = date.today().strftime("%Y-%m")
    to_call: list[str] = []

    for merchant in merchants:
        safe = try_sanitise(merchant)
        if safe is None:
            log.warning("llm_merchant_rejected_by_sanitiser", merchant_length=len(merchant))
            continue
        cached = await llm_cache_repo.get(user_id, safe, PROMPT_VERSION)
        if cached is not None:
            results[safe] = CategorySuggestion(
                merchant=safe, category_id=str(cached.category_id), confidence=cached.confidence
            )
        else:
            to_call.append(safe)

    if not to_call:
        return results

    user = await user_repo.get_by_id(user_id)
    calls_so_far = user.llm_calls_this_month if user and user.llm_calls_month == month else 0
    budget_remaining = max(0, monthly_call_cap - calls_so_far)
    if budget_remaining <= 0:
        log.info("llm_budget_exhausted", user_id=str(user_id), month=month)
        return results

    to_call = to_call[:budget_remaining]

    for i in range(0, len(to_call), BATCH_SIZE):
        batch = to_call[i : i + BATCH_SIZE]
        try:
            suggestions = await provider.categorise_batch(batch, allowed_categories)
        except LLMUnavailableError as exc:
            log.error("llm_batch_failed", provider=provider.name, error=str(exc))
            continue

        await user_repo.increment_llm_calls(user_id, month, by=len(batch))

        allowed_ids = {cid for cid, _ in allowed_categories}
        for suggestion in suggestions:
            if suggestion.category_id not in allowed_ids:
                continue
            results[suggestion.merchant] = suggestion
            await llm_cache_repo.put(
                LLMCacheEntry(
                    user_id=user_id,
                    merchant_norm=suggestion.merchant,
                    category_id=ObjectId(suggestion.category_id),
                    confidence=min(85, suggestion.confidence),
                    model=provider.model,
                    prompt_version=PROMPT_VERSION,
                )
            )

    return results
