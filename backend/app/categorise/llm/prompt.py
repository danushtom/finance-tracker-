"""Shared prompt shape for every provider (section 8.2, `prompt_version = "v1"`).

Keeping this in one place means switching provider never changes what's
asked, only who answers it — the cache key includes `prompt_version` so a
deliberate prompt change can invalidate cached results.
"""

from __future__ import annotations

import json

PROMPT_VERSION = "v1"

_SYSTEM_INSTRUCTIONS = (
    "You are classifying merchant names from Indian bank statements.\n"
    "For each merchant, return the single best category id and a confidence 0-100.\n"
    'If unsure, return "uncategorised" with a low confidence. Do not invent categories.\n'
    "Only use category ids from the allowed list. Respond with JSON only, no prose."
)


def build_prompt(merchants: list[str], allowed_categories: list[tuple[str, str]]) -> str:
    allowed = ", ".join(f'{cid}:"{name}"' for cid, name in allowed_categories)
    merchants_json = json.dumps(merchants)
    return (
        f"{_SYSTEM_INSTRUCTIONS}\n\n"
        f"Allowed categories: {allowed}\n"
        f"Merchants: {merchants_json}\n"
        'Return JSON: [{"merchant": "...", "category_id": "...", "confidence": 0-100}]'
    )


def parse_response(raw_text: str) -> list[dict]:
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("LLM response was not a JSON array")
    return data
