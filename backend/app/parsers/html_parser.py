import pandas as pd
from bs4 import BeautifulSoup

from app.parsers.base import BaseStatementParser, NormalizedStatement
from app.parsers.bank_detection import (
    detect_bank_from_columns, detect_bank_from_text, detect_account_type,
    detect_currency, detect_account_identifier,
)
from app.parsers.tabular import dataframe_to_rows
from app.core.errors import AppError, ErrorCode


class HTMLStatementParser(BaseStatementParser):
    format_name = "html"

    def can_parse(self, filename: str, sample: bytes) -> bool:
        return filename.lower().endswith((".html", ".htm"))

    def parse(self, file_path: str) -> NormalizedStatement:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()

        try:
            tables = pd.read_html(html)
        except ValueError:
            tables = []

        if not tables:
            raise AppError(ErrorCode.NO_TRANSACTIONS_FOUND, "No tables found in HTML statement.")

        df = max(tables, key=lambda d: len(d))
        df = df.astype(str)
        rows = dataframe_to_rows(df)
        if not rows:
            raise AppError(ErrorCode.NO_TRANSACTIONS_FOUND, "No transaction rows detected in HTML statement.")

        text = BeautifulSoup(html, "lxml").get_text(" ")
        bank = detect_bank_from_columns(list(df.columns))
        if bank == "Other":
            bank = detect_bank_from_text(text)

        return NormalizedStatement(
            bank_name=bank,
            account_type=detect_account_type(text),
            currency=detect_currency(text),
            account_identifier=detect_account_identifier(text),
            period_start=None,
            period_end=None,
            period_confidence=0.0,
            parser_used=self.format_name,
            rows=rows,
        )
