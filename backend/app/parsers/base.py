"""Common contracts for all statement parsers."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass
class RawTransactionRow:
    row_index: int
    transaction_date_raw: str
    description_raw: str
    debit_raw: str = ""
    credit_raw: str = ""
    amount_raw: str = ""
    type_raw: str = ""
    balance_raw: str = ""
    reference_raw: str = ""
    value_date_raw: str = ""
    date_ambiguous: bool = False


@dataclass
class NormalizedStatement:
    bank_name: str
    account_type: str
    currency: str
    account_identifier: str
    period_start: Optional[date]
    period_end: Optional[date]
    period_confidence: float
    parser_used: str
    rows: List[RawTransactionRow] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class BaseStatementParser(ABC):
    format_name: str = "generic"

    @abstractmethod
    def can_parse(self, filename: str, sample: bytes) -> bool:
        ...

    @abstractmethod
    def parse(self, file_path: str, password: Optional[str] = None) -> NormalizedStatement:
        """password is only meaningful for encrypted PDFs -- other parsers ignore it."""
        ...
