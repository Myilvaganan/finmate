from typing import Optional

import pandas as pd

from app.parsers.base import BaseStatementParser, NormalizedStatement
from app.parsers.bank_detection import (
    detect_bank_from_columns, detect_bank_from_text, detect_account_type,
    detect_currency, detect_account_identifier,
)
from app.parsers.tabular import dataframe_to_rows
from app.core.errors import AppError, ErrorCode


class TXTStatementParser(BaseStatementParser):
    format_name = "txt"

    def can_parse(self, filename: str, sample: bytes) -> bool:
        return filename.lower().endswith(".txt")

    def parse(self, file_path: str, password: Optional[str] = None) -> NormalizedStatement:
        try:
            df = pd.read_csv(
                file_path, dtype=str, sep=None, engine="python",
                keep_default_na=False, na_values=[""], skip_blank_lines=True,
            )
        except Exception as exc:
            raise AppError(ErrorCode.PARSER_FAILED, f"Could not parse TXT file: {exc}")

        if df.empty or len(df.columns) < 2:
            raise AppError(ErrorCode.NO_TRANSACTIONS_FOUND, "Could not detect a delimited table in TXT file.")

        rows = dataframe_to_rows(df)
        if not rows:
            raise AppError(ErrorCode.NO_TRANSACTIONS_FOUND, "No transaction rows detected in TXT file.")

        raw_text = " ".join(str(c) for c in df.columns)
        bank = detect_bank_from_columns(list(df.columns))
        if bank == "Other":
            bank = detect_bank_from_text(raw_text)

        return NormalizedStatement(
            bank_name=bank,
            account_type=detect_account_type(raw_text),
            currency=detect_currency(raw_text),
            account_identifier=detect_account_identifier(raw_text),
            period_start=None,
            period_end=None,
            period_confidence=0.0,
            parser_used=self.format_name,
            rows=rows,
        )
