"""Categorisation pipeline (FR-4.1, section 8.1).

Evaluated **per distinct `merchant_norm`**, not per transaction — the LLM
in particular is invoked once per merchant, ever (FR-4.2, G-2).

| # | Stage                                              | Confidence        | categorised_by |
|---|-----------------------------------------------------|-------------------|----------------|
| 1 | Exact user rule                                      | 100               | rule           |
| 2 | Merchant memory, source="user"                       | 98                | user           |
| 3 | Pattern user rule (contains/starts_with/regex)       | 95                | rule           |
| 4 | Seed rule pack                                       | 90                | rule           |
| 5 | Merchant memory, source="llm" (cache hit)            | stored            | llm            |
| 6 | Fuzzy match vs. merchant memory, token_set_ratio>=88 | min(88, score)    | fuzzy          |
| 7 | LLM fallback (batched)                               | min(85, conf)     | llm            |
| 8 | Nothing matched                                      | 0 -> Uncategorised| none           |

Amount-conditional rules (FR-4.10) are applied per-transaction *after* this
merchant-level result, in `apply_amount_conditional_override`, and can
override it.
"""

from __future__ import annotations

from dataclasses import dataclass

from bson import ObjectId

from app.categorise.fuzzy import find_best_match
from app.categorise.llm.base import LLMProvider
from app.categorise.llm_batch import categorise_unknown_merchants
from app.categorise.rules import RuleSet
from app.models.merchant import Merchant, MerchantSource
from app.models.rule import MatchType, Rule, RuleSource
from app.repositories.categories import CategoryRepository
from app.repositories.llm_cache import LLMCacheRepository
from app.repositories.merchants import MerchantRepository
from app.repositories.users import UserRepository


@dataclass
class CategoryResult:
    category_id: ObjectId | None
    subcategory_id: ObjectId | None
    confidence: int
    categorised_by: str  # "rule" | "user" | "fuzzy" | "llm" | "none"


UNCATEGORISED = CategoryResult(category_id=None, subcategory_id=None, confidence=0, categorised_by="none")


def _split_rule_sets(rules: list[Rule]) -> tuple[RuleSet, RuleSet, RuleSet]:
    user_exact = [r for r in rules if r.source == RuleSource.USER and r.match_type == MatchType.EXACT]
    user_pattern = [r for r in rules if r.source == RuleSource.USER and r.match_type != MatchType.EXACT]
    seed = [r for r in rules if r.source != RuleSource.USER]
    return RuleSet(user_exact), RuleSet(user_pattern), RuleSet(seed)


async def categorise_merchants(
    *,
    user_id: ObjectId,
    merchant_norms: list[str],
    rules: list[Rule],
    merchant_repo: MerchantRepository,
    category_repo: CategoryRepository,
    llm_cache_repo: LLMCacheRepository,
    user_repo: UserRepository,
    llm_provider: LLMProvider | None,
    llm_monthly_call_cap: int,
) -> dict[str, CategoryResult]:
    user_exact, user_pattern, seed = _split_rule_sets(rules)
    known_merchants = await merchant_repo.find(user_id, limit=0)
    known_by_norm = {m.merchant_norm: m for m in known_merchants}

    results: dict[str, CategoryResult] = {}
    needs_llm: list[str] = []
    needs_fuzzy: list[str] = []

    for merchant_norm in set(merchant_norms):
        rule = user_exact.match(merchant_norm)
        if rule:
            results[merchant_norm] = CategoryResult(rule.category_id, rule.subcategory_id, 100, "rule")
            continue

        memory = known_by_norm.get(merchant_norm)
        if memory and memory.source == MerchantSource.USER:
            results[merchant_norm] = CategoryResult(memory.category_id, memory.subcategory_id, 98, "user")
            continue

        rule = user_pattern.match(merchant_norm)
        if rule:
            results[merchant_norm] = CategoryResult(rule.category_id, rule.subcategory_id, 95, "rule")
            continue

        rule = seed.match(merchant_norm)
        if rule:
            results[merchant_norm] = CategoryResult(rule.category_id, rule.subcategory_id, 90, "rule")
            continue

        if memory and memory.source == MerchantSource.LLM:
            results[merchant_norm] = CategoryResult(
                memory.category_id, memory.subcategory_id, memory.confidence, "llm"
            )
            continue

        needs_fuzzy.append(merchant_norm)

    for merchant_norm in needs_fuzzy:
        fuzzy_match = find_best_match(merchant_norm, known_merchants)
        if fuzzy_match:
            results[merchant_norm] = CategoryResult(
                fuzzy_match.merchant.category_id,
                fuzzy_match.merchant.subcategory_id,
                fuzzy_match.confidence,
                "fuzzy",
            )
        else:
            needs_llm.append(merchant_norm)

    if needs_llm and llm_provider is not None:
        categories = await category_repo.find(user_id, {"archived": False})
        allowed = [(str(c.id), c.name) for c in categories]
        name_to_id = {c.name: c.id for c in categories}

        suggestions = await categorise_unknown_merchants(
            user_id=user_id,
            merchants=needs_llm,
            allowed_categories=allowed,
            provider=llm_provider,
            llm_cache_repo=llm_cache_repo,
            user_repo=user_repo,
            monthly_call_cap=llm_monthly_call_cap,
        )
        for merchant_norm in needs_llm:
            suggestion = suggestions.get(merchant_norm)
            if suggestion and suggestion.category_id in {str(v) for v in name_to_id.values()}:
                results[merchant_norm] = CategoryResult(
                    ObjectId(suggestion.category_id), None, min(85, suggestion.confidence), "llm"
                )
            else:
                results[merchant_norm] = UNCATEGORISED
    else:
        for merchant_norm in needs_llm:
            results[merchant_norm] = UNCATEGORISED

    return results


def apply_amount_conditional_override(
    result: CategoryResult, rules: list[Rule], merchant_norm: str, direction: str, amount_minor: int
) -> CategoryResult:
    """FR-4.10: amount-conditional rules are evaluated per transaction,
    after the merchant-level result, and can override it."""
    amount_rules = [
        r
        for r in rules
        if (r.amount_min_minor is not None or r.amount_max_minor is not None)
        and r.pattern.upper() in merchant_norm
        and r.enabled
    ]
    for rule in sorted(amount_rules, key=lambda r: r.priority, reverse=True):
        abs_amount = abs(amount_minor)
        if rule.amount_min_minor is not None and abs_amount < rule.amount_min_minor:
            continue
        if rule.amount_max_minor is not None and abs_amount > rule.amount_max_minor:
            continue
        if rule.direction and rule.direction != direction:
            continue
        return CategoryResult(rule.category_id, rule.subcategory_id, 100, "rule")
    return result
