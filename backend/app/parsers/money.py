"""Indian bank-statement money and date parsing (FR-2.9, FR-2.10, NFR-5, NFR-16).

`Paise` (an alias for `int`) is the ONLY currency type anywhere in the
backend. Parsing goes through `Decimal` and is quantized before conversion
to an integer minor unit — floats never enter the calculation (NFR-5).
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

Paise = int

_CR_DR_RE = re.compile(r"\s*(Cr|Dr|CR|DR)\.?\s*$")
_PAREN_RE = re.compile(r"^\((.*)\)$")
_NUMERIC_CLEAN_RE = re.compile(r"[^\d.\-]")

_DATE_FORMATS = [
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d-%b-%y",
    "%d-%b-%Y",
    "%Y-%m-%d",
    "%d/%m/%y",
    "%d %b %Y",
    "%d %B %Y",
]


class MoneyParseError(ValueError):
    pass


def to_minor(raw: str | None) -> Paise | None:
    """'1,43,000.50' | '1,450.00 Cr' | '(2,000.00)' | '₹500' -> signed paise.

    Sign convention: a trailing `Dr` or a value already negative/parenthesised
    is negative (outflow); a trailing `Cr` or a plain positive value is
    positive (inflow). Callers that know the column's direction (a dedicated
    debit vs. credit column) should derive the final sign themselves and can
    pass the absolute value here.
    """
    if raw is None:
        return None
    s = raw.strip()
    if not s or s in {"-", "—", "NA", "N/A"}:
        return None

    s = s.replace("₹", "").replace("Rs.", "").replace("Rs", "").replace("INR", "").strip()

    sign = 1
    cr_dr_match = _CR_DR_RE.search(s)
    if cr_dr_match:
        marker = cr_dr_match.group(1).upper()
        s = _CR_DR_RE.sub("", s)
        if marker == "DR":
            sign = -1

    paren_match = _PAREN_RE.match(s.strip())
    if paren_match:
        s = paren_match.group(1)
        sign = -1

    s = s.strip()
    if s.startswith("-"):
        sign = -1
        s = s[1:]
    elif s.startswith("+"):
        s = s[1:]

    cleaned = _NUMERIC_CLEAN_RE.sub("", s)
    if not cleaned or cleaned == "-":
        return None

    try:
        value = Decimal(cleaned)
    except InvalidOperation as exc:
        raise MoneyParseError(f"Could not parse amount: {raw!r}") from exc

    value = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    minor = int(value * 100)
    return sign * minor


def format_inr_minor(minor: Paise) -> str:
    """Display-only helper mirroring the frontend's `formatINR` (section 6).
    Never used for arithmetic."""
    rupees = minor / 100
    sign = "-" if rupees < 0 else ""
    rupees = abs(rupees)
    whole = int(rupees)
    s = str(whole)
    if len(s) > 3:
        last3 = s[-3:]
        rest = s[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        s = ",".join([*groups, last3])
    return f"{sign}₹{s}"


def split_minor(amount: Paise, weights: list[int]) -> list[Paise]:
    """Split `amount` proportionally to `weights` without losing a paisa.

    Assigns floor shares to every part, then hands out the remainder
    (`amount - sum(floors)`) one paisa at a time to the parts with the
    largest fractional remainder (largest-remainder method), so
    `sum(parts) == amount` always holds, even for negative amounts or
    weights that don't divide evenly.
    """
    total_weight = sum(weights)
    if total_weight == 0:
        raise ValueError("split_minor requires at least one non-zero weight")

    sign = 1 if amount >= 0 else -1
    abs_amount = abs(amount)

    raw_shares = [Decimal(abs_amount) * Decimal(w) / Decimal(total_weight) for w in weights]
    floors = [int(r) for r in raw_shares]
    remainder = abs_amount - sum(floors)

    fractional = sorted(
        range(len(weights)), key=lambda i: (raw_shares[i] - floors[i]), reverse=True
    )
    for i in fractional[:remainder]:
        floors[i] += 1

    return [sign * f for f in floors]


def parse_statement_date(raw: str, *, day_first: bool = True) -> date:
    """FR-2.9: tries an explicit format list, day-first by default (Indian
    convention); the ambiguous-date assumption is surfaced to the caller via
    `day_first` so the UI can show it."""
    s = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue

    # Fall back to dateutil for looser formats, honouring day-first.
    from dateutil import parser as dateutil_parser

    try:
        return dateutil_parser.parse(s, dayfirst=day_first).date()
    except (ValueError, OverflowError) as exc:
        raise MoneyParseError(f"Could not parse date: {raw!r}") from exc


def month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"
