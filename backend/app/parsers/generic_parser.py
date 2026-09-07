"""Fallback for unrecognized tabular layouts: tries the most permissive column heuristics."""
import pandas as pd

from app.parsers.base import BaseStatementParser, NormalizedStatement
from app.parsers.bank_detection import detect_account_type, detect_currency
from app.parsers.tabular import dataframe_to_rows
from app.core.errors import AppError, ErrorCode


class GenericStatementParser(BaseStatementParser):
    format_name = "generic"

    def can_parse(self, filename: str, sample: bytes) -> bool:
        return True

    def parse(self, file_path: str) -> NormalizedStatement:
        df = None
        for reader in (
            lambda p: pd.read_csv(p, dtype=str, sep=None, engine="python"),
            lambda p: pd.read_excel(p, dtype=str),
        ):
            try:
                df = reader(file_path)
                if df is not None and not df.empty:
                    break
            except Exception:
                continue

        if df is None or df.empty:
            raise AppError(
                ErrorCode.UNSUPPORTED_FORMAT,
                "Could not recognize this statement format. Please try CSV or XLSX export from your bank.",
            )

        rows = dataframe_to_rows(df.astype(str))
        if not rows:
            raise AppError(ErrorCode.NO_TRANSACTIONS_FOUND, "No transaction rows detected.")

        raw_text = " ".join(str(c) for c in df.columns)
        return NormalizedStatement(
            bank_name="Other",
            account_type=detect_account_type(raw_text),
            currency=detect_currency(raw_text),
            account_identifier="",
            period_start=None,
            period_end=None,
            period_confidence=0.0,
            parser_used=self.format_name,
            rows=rows,
            warnings=["Statement format not recognized; parsed using generic detection. Please review carefully."],
        )
