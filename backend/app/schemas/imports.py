from __future__ import annotations

from pydantic import BaseModel

from app.parsers.base import ColumnMapping


class ImportCreatedResponse(BaseModel):
    import_id: str


class MappingSubmitRequest(BaseModel):
    date: str | None = None
    description: str | None = None
    debit: str | None = None
    credit: str | None = None
    amount: str | None = None
    balance: str | None = None
    ref: str | None = None
    header_row_index: int = 0

    def to_mapping(self) -> ColumnMapping:
        return ColumnMapping(
            date=self.date,
            description=self.description,
            debit=self.debit,
            credit=self.credit,
            amount=self.amount,
            balance=self.balance,
            ref=self.ref,
            header_row_index=self.header_row_index,
        )
