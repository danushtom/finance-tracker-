"""Merchant description normalisation (FR-3.1, section 7.4).

An ordered list of named regex steps, each independently unit-testable
against a fixture corpus of real (anonymised) descriptions:

    "UPI/DR/451233098711/SWIGGY/HDFC/swiggyupi@axis/Payment from Ph"
        -> strip rails prefix (UPI|IMPS|NEFT|RTGS|POS|ACH|MMT|CMS/...)
        -> strip digit runs >= 4, dates, times, terminal ids, ref numbers
        -> extract VPA -> counterparty_vpa
        -> uppercase, collapse whitespace, strip punctuation
        -> "SWIGGY HDFC"

`description_raw` is never mutated — this only ever produces the derived
`merchant_norm` (and optionally a `counterparty_vpa`) alongside it.

Note: `ATM` is deliberately **not** treated as rails-prefix noise — unlike
UPI/IMPS/NEFT/etc. (pure routing metadata), it is itself merchant-
identifying: it's what lets the seed rule pack (FR-4.11) recognise cash
withdrawals ("ATM WDL", "ATM CASH").
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_RAILS_PREFIX_RE = re.compile(
    r"^(UPI|IMPS|NEFT|RTGS|POS|ACH|MMT|CMS|ECS|NACH)[\s/\-:]+", re.IGNORECASE
)
_VPA_RE = re.compile(r"\b[\w.\-]{2,}@[a-zA-Z]{2,}\b")
_DIGIT_RUN_RE = re.compile(r"\b\d{4,}\b")
# A short letter-prefixed reference/cheque number, e.g. "N012345678901" —
# removed entirely, unlike a bank code (see below), because a 1-2 letter
# prefix is never itself merchant-identifying.
_REF_TOKEN_RE = re.compile(r"\b[A-Za-z]{1,2}\d{6,}\b")
# A bank/branch code glued to a digit run with no separator, e.g. an IFSC-
# style suffix in "HDFC0001234" -> "HDFC". Requires >=3 letters so it reads
# as a code (kept) rather than a reference number (dropped, above).
_GLUED_TRAILING_DIGITS_RE = re.compile(r"\b([A-Za-z]{3,})\d{4,}\b")
_DATE_RE = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")
_TIME_RE = re.compile(r"\b\d{1,2}:\d{2}(:\d{2})?\b")
_PUNCT_RE = re.compile(r"[^\w\s&]")
_WHITESPACE_RE = re.compile(r"\s+")
_SEPARATOR_RE = re.compile(r"[/\-:|]+")

# Common noise tokens that survive the above steps and add nothing —
# includes the UPI debit/credit marker ("UPI/DR/...", "UPI/CR/...") since
# it's positional rails metadata, not part of the rails-prefix regex.
_NOISE_TOKENS = {
    "PAYMENT", "FROM", "TO", "PH", "TRANSFER", "TXN", "REF", "NO", "AND", "THE", "DR", "CR",
}


@dataclass
class NormaliseResult:
    merchant_norm: str
    counterparty_vpa: str | None


def extract_vpa(description: str) -> str | None:
    match = _VPA_RE.search(description)
    return match.group(0).lower() if match else None


def normalise_merchant(description: str) -> NormaliseResult:
    text = description.strip()

    vpa = extract_vpa(text)

    text = _RAILS_PREFIX_RE.sub("", text)
    text = _VPA_RE.sub(" ", text)
    text = _DATE_RE.sub(" ", text)
    text = _TIME_RE.sub(" ", text)
    text = _REF_TOKEN_RE.sub(" ", text)
    text = _GLUED_TRAILING_DIGITS_RE.sub(r"\1", text)
    text = _DIGIT_RUN_RE.sub(" ", text)
    text = _SEPARATOR_RE.sub(" ", text)
    text = _PUNCT_RE.sub(" ", text)

    text = text.upper()
    tokens = [t for t in _WHITESPACE_RE.split(text) if t and t not in _NOISE_TOKENS]
    merchant_norm = " ".join(tokens).strip()

    if not merchant_norm:
        merchant_norm = "UNKNOWN"

    return NormaliseResult(merchant_norm=merchant_norm, counterparty_vpa=vpa)
