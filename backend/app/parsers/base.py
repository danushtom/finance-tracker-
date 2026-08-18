"""Parser protocol shared by CSV/XLSX/PDF adapters (section 7.1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Protocol


@dataclass
class RawRow:
    date: str | None
    description: str | None
    debit: str | None
    credit: str | None
    amount: str | None
    balance: str | None
    ref: str | None
    row_index: int


@dataclass
class Preview:
    headers: list[str]
    rows: list[list[str]]
    needs_mapping: bool = False
    text_preview: str | None = None  # for unparseable PDFs (FR-2.7)


@dataclass
class ColumnMapping:
    date: str | None = None
    description: str | None = None
    debit: str | None = None
    credit: str | None = None
    amount: str | None = None
    balance: str | None = None
    ref: str | None = None
    header_row_index: int = 0

    def as_dict(self) -> dict:
        return {
            "date": self.date,
            "description": self.description,
            "debit": self.debit,
            "credit": self.credit,
            "amount": self.amount,
            "balance": self.balance,
            "ref": self.ref,
            "header_row_index": self.header_row_index,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ColumnMapping":
        return cls(**{k: d.get(k) for k in cls.__dataclass_fields__})


class StatementParser(Protocol):
    def sniff(self, path: Path) -> float:
        """Confidence in [0, 1] that this parser can handle `path`."""
        ...

    def preview(self, path: Path, *, password: str | None = None) -> Preview:
        ...

    def parse(
        self, path: Path, *, mapping: ColumnMapping | None = None, password: str | None = None
    ) -> Iterator[RawRow]:
        ...
