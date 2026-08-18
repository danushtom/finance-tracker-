from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Iterator

from app.parsers.base import ColumnMapping, Preview, RawRow
from app.parsers.column_map import detect_header, mapping_from_detection


def _sniff_dialect(sample: str) -> csv.Dialect:
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        return csv.excel  # type: ignore[return-value]


def _read_all_rows(path: Path) -> list[list[str]]:
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig", errors="replace")
    dialect = _sniff_dialect(text[:4096])
    reader = csv.reader(io.StringIO(text), dialect)
    return [row for row in reader if any(cell.strip() for cell in row)]


class CsvParser:
    def sniff(self, path: Path) -> float:
        return 1.0 if path.suffix.lower() == ".csv" else 0.0

    def preview(self, path: Path, *, password: str | None = None) -> Preview:
        rows = _read_all_rows(path)
        detection = detect_header(rows)
        if detection.header_row_index is None:
            return Preview(headers=[], rows=rows[:10], needs_mapping=True)
        header_row = rows[detection.header_row_index]
        data_rows = rows[detection.header_row_index + 1 : detection.header_row_index + 11]
        mapping = mapping_from_detection(detection, header_row)
        return Preview(headers=header_row, rows=data_rows, needs_mapping=mapping is None)

    def parse(
        self, path: Path, *, mapping: ColumnMapping | None = None, password: str | None = None
    ) -> Iterator[RawRow]:
        rows = _read_all_rows(path)
        if mapping is None:
            detection = detect_header(rows)
            if detection.header_row_index is None:
                return
            header_row = rows[detection.header_row_index]
            mapping = mapping_from_detection(detection, header_row)
            if mapping is None:
                return

        header_row = rows[mapping.header_row_index]
        col_index = {name: header_row.index(name) for name in header_row}

        def cell(row: list[str], field_name: str | None) -> str | None:
            if not field_name or field_name not in col_index:
                return None
            idx = col_index[field_name]
            return row[idx] if idx < len(row) else None

        for i, row in enumerate(rows[mapping.header_row_index + 1 :]):
            yield RawRow(
                date=cell(row, mapping.date),
                description=cell(row, mapping.description),
                debit=cell(row, mapping.debit),
                credit=cell(row, mapping.credit),
                amount=cell(row, mapping.amount),
                balance=cell(row, mapping.balance),
                ref=cell(row, mapping.ref),
                row_index=i,
            )
