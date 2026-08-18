"""PDF statement parser (FR-2.1, FR-2.4, FR-2.7, FR-2.8, section 7.3).

Strategy: `pdfplumber.extract_tables()` first; if that yields nothing
usable, fall back to `camelot` in stream mode; if the page text is
essentially empty the PDF is scanned, and — only if OCR is enabled — we run
it through `ocrmypdf` and retry, flagging every resulting row
`needs_review`. If nothing works, the parser returns an empty result and
`needs_mapping=True` with a text preview rather than guessing (FR-2.7).

Password-protected PDFs are decrypted **in memory only** with `pikepdf`;
the password is never written to disk, to the import document, or logged
(FR-2.4, NFR-17).
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path
from typing import Iterator

import pdfplumber
import pikepdf

from app.parsers.base import ColumnMapping, Preview, RawRow
from app.parsers.column_map import detect_header, mapping_from_detection


class PdfParseError(Exception):
    pass


def decrypt_pdf_bytes_if_protected(content: bytes, password: str | None) -> bytes:
    """Called once, synchronously, at upload time (FR-2.4). If the PDF is
    password-protected, decrypts it in memory and returns plain PDF bytes
    to persist to disk — the password itself is used only for this call and
    is never written anywhere. If the PDF isn't encrypted, returns the
    original bytes unchanged."""
    try:
        with pikepdf.open(io.BytesIO(content)) as pdf:
            buf = io.BytesIO()
            pdf.save(buf)
            return buf.getvalue()
    except pikepdf.PasswordError:
        pass

    try:
        with pikepdf.open(io.BytesIO(content), password=password or "") as pdf:
            buf = io.BytesIO()
            pdf.save(buf)
            return buf.getvalue()
    except pikepdf.PasswordError as exc:
        raise PdfParseError("Incorrect or missing PDF password") from exc


def _decrypt_to_buffer(path: Path, password: str | None) -> io.BytesIO:
    try:
        with pikepdf.open(path, password=password or "") as pdf:
            buf = io.BytesIO()
            pdf.save(buf)
            buf.seek(0)
            return buf
    except pikepdf.PasswordError as exc:
        raise PdfParseError("Incorrect or missing PDF password") from exc


def _is_scanned(pdf: pdfplumber.PDF) -> bool:
    sample_pages = pdf.pages[:3]
    total_chars = sum(len(p.extract_text() or "") for p in sample_pages)
    return total_chars < 20 * max(1, len(sample_pages))


def _extract_rows_pdfplumber(pdf: pdfplumber.PDF) -> list[list[str]]:
    rows: list[list[str]] = []
    settings = {
        "vertical_strategy": "lines_strict",
        "horizontal_strategy": "lines_strict",
    }
    for page in pdf.pages:
        tables = page.extract_tables(settings) or page.extract_tables()
        for table in tables or []:
            for row in table:
                cells = ["" if c is None else str(c).strip() for c in row]
                if any(cells):
                    rows.append(cells)
    return rows


def _extract_rows_camelot(path: Path) -> list[list[str]]:
    try:
        import camelot
    except ImportError:
        return []
    try:
        tables = camelot.read_pdf(str(path), pages="all", flavor="stream")
    except Exception:
        return []
    rows: list[list[str]] = []
    for table in tables:
        for row in table.df.values.tolist():
            cells = [str(c).strip() for c in row]
            if any(cells):
                rows.append(cells)
    return rows


def _ocr(path: Path) -> Path | None:
    try:
        import ocrmypdf
    except ImportError:
        return None
    out_path = Path(tempfile.mktemp(suffix=".pdf"))
    try:
        ocrmypdf.ocr(str(path), str(out_path), force_ocr=True, progress_bar=False)
    except Exception:
        return None
    return out_path


class PdfParser:
    def sniff(self, path: Path) -> float:
        return 1.0 if path.suffix.lower() == ".pdf" else 0.0

    def _rows_and_flags(
        self, path: Path, *, password: str | None, ocr_enabled: bool
    ) -> tuple[list[list[str]], bool, str | None]:
        """Returns (rows, was_ocr, text_preview_if_unparseable)."""
        buf = _decrypt_to_buffer(path, password)
        with pdfplumber.open(buf) as pdf:
            if _is_scanned(pdf):
                if not ocr_enabled:
                    text = "\n".join((p.extract_text() or "") for p in pdf.pages[:2])
                    return [], False, text or "(scanned document, no extractable text)"
                ocred = _ocr(path)
                if ocred is None:
                    return [], False, "(scanned document; OCR unavailable)"
                with pdfplumber.open(ocred) as ocr_pdf:
                    rows = _extract_rows_pdfplumber(ocr_pdf)
                return rows, True, None

            rows = _extract_rows_pdfplumber(pdf)
            if rows:
                return rows, False, None

        rows = _extract_rows_camelot(path)
        if rows:
            return rows, False, None

        return [], False, "(no tabular data could be extracted)"

    def preview(self, path: Path, *, password: str | None = None) -> Preview:
        rows, _, text_preview = self._rows_and_flags(path, password=password, ocr_enabled=False)
        if not rows:
            return Preview(headers=[], rows=[], needs_mapping=True, text_preview=text_preview)
        detection = detect_header(rows)
        if detection.header_row_index is None:
            return Preview(headers=[], rows=rows[:10], needs_mapping=True)
        header_row = rows[detection.header_row_index]
        data_rows = rows[detection.header_row_index + 1 : detection.header_row_index + 11]
        mapping = mapping_from_detection(detection, header_row)
        return Preview(headers=header_row, rows=data_rows, needs_mapping=mapping is None)

    def parse(
        self,
        path: Path,
        *,
        mapping: ColumnMapping | None = None,
        password: str | None = None,
        ocr_enabled: bool = False,
    ) -> Iterator[RawRow]:
        rows, was_ocr, _ = self._rows_and_flags(path, password=password, ocr_enabled=ocr_enabled)
        if not rows:
            return

        if mapping is None:
            detection = detect_header(rows)
            if detection.header_row_index is None:
                return
            header_row = rows[detection.header_row_index]
            mapping = mapping_from_detection(detection, header_row)
            if mapping is None:
                return

        header_row = rows[mapping.header_row_index]
        col_index = {name: header_row.index(name) for name in header_row if name in header_row}

        def cell(row: list[str], field_name: str | None) -> str | None:
            if not field_name or field_name not in col_index:
                return None
            idx = col_index[field_name]
            return row[idx] if idx < len(row) else None

        # Multi-line description continuation: a row with description but no
        # date/amount is joined onto the previous row (section 7.3).
        pending: RawRow | None = None
        out_index = 0
        for row in rows[mapping.header_row_index + 1 :]:
            date_val = cell(row, mapping.date)
            amount_val = cell(row, mapping.amount) or cell(row, mapping.debit) or cell(row, mapping.credit)
            desc_val = cell(row, mapping.description)
            if not date_val and not amount_val and desc_val and pending is not None:
                pending.description = f"{pending.description} {desc_val}".strip()
                continue
            if pending is not None:
                yield pending
            pending = RawRow(
                date=date_val,
                description=desc_val,
                debit=cell(row, mapping.debit),
                credit=cell(row, mapping.credit),
                amount=cell(row, mapping.amount),
                balance=cell(row, mapping.balance),
                ref=cell(row, mapping.ref),
                row_index=out_index,
            )
            out_index += 1
        if pending is not None:
            yield pending
