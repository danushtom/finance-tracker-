from __future__ import annotations

from pathlib import Path

from app.parsers.base import StatementParser
from app.parsers.csv_parser import CsvParser
from app.parsers.pdf_parser import PdfParser
from app.parsers.xlsx_parser import XlsxParser

_PARSERS: list[StatementParser] = [CsvParser(), XlsxParser(), PdfParser()]


def select_parser(path: Path) -> tuple[StatementParser, str]:
    """Selection: by extension first, then `sniff()` (section 7.1)."""
    best: tuple[StatementParser, float] | None = None
    for parser in _PARSERS:
        score = parser.sniff(path)
        if score > 0 and (best is None or score > best[1]):
            best = (parser, score)
    if best is None:
        raise ValueError(f"No parser can handle file: {path.name}")
    parser = best[0]
    name = type(parser).__name__.replace("Parser", "").lower()
    return parser, name
