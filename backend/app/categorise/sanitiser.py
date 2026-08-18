"""LLM egress sanitiser (NFR-10, section 8.2).

Only the normalised merchant string is ever sent to an LLM — never full
descriptions, amounts, account numbers, balances, or user identity. This
constraint is enforced in code, immediately before every outbound call, not
just by convention: `sanitise_merchant` raises `UnsafeMerchantError` if the
string still contains anything that looks like a digit run, an `@` (VPA
fragment), or a currency symbol. A failed assertion means the merchant is
dropped to `Uncategorised` rather than sent (section 8.2).
"""

from __future__ import annotations

import re

_DIGIT_RUN_RE = re.compile(r"\d{4,}")
_CURRENCY_RE = re.compile(r"[₹$€£]")
_MAX_LEN = 64


class UnsafeMerchantError(ValueError):
    pass


def sanitise_merchant(merchant_norm: str) -> str:
    if not merchant_norm:
        raise UnsafeMerchantError("empty merchant string")
    if len(merchant_norm) > _MAX_LEN:
        raise UnsafeMerchantError("merchant string exceeds max length")
    if "@" in merchant_norm:
        raise UnsafeMerchantError("merchant string contains an '@' (possible VPA fragment)")
    if _DIGIT_RUN_RE.search(merchant_norm):
        raise UnsafeMerchantError("merchant string contains a digit run >= 4 (possible account/ref number)")
    if _CURRENCY_RE.search(merchant_norm):
        raise UnsafeMerchantError("merchant string contains a currency symbol")
    return merchant_norm


def try_sanitise(merchant_norm: str) -> str | None:
    try:
        return sanitise_merchant(merchant_norm)
    except UnsafeMerchantError:
        return None
