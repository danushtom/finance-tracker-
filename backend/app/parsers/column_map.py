"""Header-row detection for CSV/XLSX (FR-2.6, section 7.2).

Bank statements are usually full of preamble (account holder name, address,
statement period, disclaimers) before the actual header row. We score every
one of the first 30 rows as a header candidate against a synonym table and
take the best-scoring row above threshold; everything above it is discarded.
"""

from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz

from app.parsers.base import ColumnMapping

SYNONYMS: dict[str, list[str]] = {
    "date": ["date", "txn date", "transaction date", "value date", "posting date"],
    "description": ["description", "narration", "particulars", "remarks", "details", "transaction remarks"],
    "debit": ["debit", "withdrawal", "withdrawal amt", "withdrawal amt.", "dr", "debit amount"],
    "credit": ["credit", "deposit", "deposit amt", "deposit amt.", "cr", "credit amount"],
    "amount": ["amount", "transaction amount", "amt"],
    "balance": ["balance", "closing balance", "running balance", "available balance"],
    "ref": ["ref", "ref no", "ref no.", "cheque no", "chq no", "utr", "reference", "reference no"],
}

HEADER_SCORE_THRESHOLD = 60  # per matched cell, out of 100
MIN_MATCHED_FIELDS = 3
MAX_PREAMBLE_ROWS = 30


@dataclass
class HeaderDetection:
    header_row_index: int | None
    column_roles: dict[int, str]  # column index -> canonical field name
    score: float


def _score_cell(cell: str) -> tuple[str | None, float]:
    cell_norm = cell.strip().lower()
    if not cell_norm:
        return None, 0.0
    best_field, best_score = None, 0.0
    for field_name, synonyms in SYNONYMS.items():
        for syn in synonyms:
            score = fuzz.ratio(cell_norm, syn)
            if score > best_score:
                best_field, best_score = field_name, score
    return best_field, best_score


def detect_header(rows: list[list[str]]) -> HeaderDetection:
    best = HeaderDetection(header_row_index=None, column_roles={}, score=0.0)
    for row_idx, row in enumerate(rows[:MAX_PREAMBLE_ROWS]):
        roles: dict[int, str] = {}
        total_score = 0.0
        matched_fields: set[str] = set()
        for col_idx, cell in enumerate(row):
            field_name, score = _score_cell(str(cell))
            if field_name and score >= HEADER_SCORE_THRESHOLD and field_name not in matched_fields:
                roles[col_idx] = field_name
                matched_fields.add(field_name)
                total_score += score
        if len(matched_fields) >= MIN_MATCHED_FIELDS and total_score > best.score:
            best = HeaderDetection(header_row_index=row_idx, column_roles=roles, score=total_score)
    return best


def mapping_from_detection(detection: HeaderDetection, headers: list[str]) -> ColumnMapping | None:
    if detection.header_row_index is None:
        return None
    mapping = ColumnMapping(header_row_index=detection.header_row_index)
    for col_idx, field_name in detection.column_roles.items():
        if col_idx < len(headers):
            setattr(mapping, field_name, headers[col_idx])
    # A usable mapping needs a date, a description, and either a
    # debit/credit pair or a single amount column.
    if mapping.date and mapping.description and (mapping.amount or (mapping.debit or mapping.credit)):
        return mapping
    return None
