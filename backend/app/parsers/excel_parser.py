import pandas as pd

from app.parsers.base import BaseStatementParser, NormalizedStatement
from app.parsers.bank_detection import (
    detect_bank_from_columns, detect_bank_from_text, detect_account_type,
    detect_currency, detect_account_identifier,
)
from app.parsers.tabular import dataframe_to_rows
from app.core.errors import AppError, ErrorCode


class ExcelStatementParser(BaseStatementParser):
    format_name = "xlsx"

    def can_parse(self, filename: str, sample: bytes) -> bool:
        return filename.lower().endswith((".xlsx", ".xls"))

    def parse(self, file_path: str) -> NormalizedStatement:
        try:
            sheets = pd.read_excel(file_path, dtype=str, sheet_name=None)
        except Exception as exc:
            raise AppError(ErrorCode.PARSER_FAILED, f"Could not parse Excel file: {exc}")

        # Pick the sheet with the most rows -- statements are usually the largest sheet.
        df = max(sheets.values(), key=lambda d: len(d), default=None)
        if df is None or df.empty:
            raise AppError(ErrorCode.NO_TRANSACTIONS_FOUND, "No rows found in Excel file.")

        # Bank exports sometimes have a few metadata rows before the real header row.
        df = _find_header_row(df)

        rows = dataframe_to_rows(df)
        if not rows:
            raise AppError(ErrorCode.NO_TRANSACTIONS_FOUND, "No transaction rows detected in Excel file.")

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


def _find_header_row(df: pd.DataFrame) -> pd.DataFrame:
    """If the first row's columns look generic (Unnamed: N), scan the first 10 rows for a real header."""
    if not all(str(c).lower().startswith("unnamed") for c in df.columns):
        return df
    for i in range(min(10, len(df))):
        candidate = [str(v).strip().lower() for v in df.iloc[i].tolist()]
        if any(k in candidate for k in ("date", "description", "narration", "particulars")):
            new_df = df.iloc[i + 1:].copy()
            new_df.columns = df.iloc[i].tolist()
            return new_df.reset_index(drop=True)
    return df
