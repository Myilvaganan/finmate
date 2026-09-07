import re
from typing import List

import pandas as pd
import pdfplumber

from app.parsers.base import BaseStatementParser, NormalizedStatement
from app.parsers.bank_detection import (
    detect_bank_from_columns, detect_bank_from_text, detect_account_type,
    detect_currency, detect_account_identifier,
)
from app.parsers.tabular import dataframe_to_rows
from app.core.errors import AppError, ErrorCode

PERIOD_RE = re.compile(
    r"(?:statement period|for the period|period)\s*[:\-]?\s*"
    r"(\d{1,2}[/\-][A-Za-z0-9]{2,4}[/\-]\d{2,4})\s*(?:to|-|–)\s*(\d{1,2}[/\-][A-Za-z0-9]{2,4}[/\-]\d{2,4})",
    re.I,
)


class PDFStatementParser(BaseStatementParser):
    format_name = "pdf"

    def can_parse(self, filename: str, sample: bytes) -> bool:
        return filename.lower().endswith(".pdf") or sample.startswith(b"%PDF")

    def parse(self, file_path: str) -> NormalizedStatement:
        all_tables: List[pd.DataFrame] = []
        full_text = ""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    full_text += (page.extract_text() or "") + "\n"
                    for table in page.extract_tables():
                        if table and len(table) > 1:
                            header, *body = table
                            header = [str(h or f"col_{i}") for i, h in enumerate(header)]
                            all_tables.append(pd.DataFrame(body, columns=header))
        except Exception as exc:
            raise AppError(ErrorCode.PARSER_FAILED, f"Could not parse PDF file: {exc}")

        if not all_tables:
            raise AppError(
                ErrorCode.NO_TRANSACTIONS_FOUND,
                "No transaction tables found in PDF. It may be a scanned image — try OCR upload.",
            )

        df = pd.concat(all_tables, ignore_index=True).astype(str)
        rows = dataframe_to_rows(df)
        if not rows:
            raise AppError(ErrorCode.NO_TRANSACTIONS_FOUND, "No transaction rows detected in PDF tables.")

        bank = detect_bank_from_columns(list(df.columns))
        if bank == "Other":
            bank = detect_bank_from_text(full_text)

        period_start_raw, period_end_raw, period_conf = None, None, 0.0
        match = PERIOD_RE.search(full_text)
        if match:
            period_start_raw, period_end_raw, period_conf = match.group(1), match.group(2), 0.9

        from app.utils.dates import parse_transaction_date
        period_start = parse_transaction_date(period_start_raw) if period_start_raw else None
        period_end = parse_transaction_date(period_end_raw) if period_end_raw else None

        return NormalizedStatement(
            bank_name=bank,
            account_type=detect_account_type(full_text),
            currency=detect_currency(full_text),
            account_identifier=detect_account_identifier(full_text),
            period_start=period_start,
            period_end=period_end,
            period_confidence=period_conf if period_start and period_end else 0.0,
            parser_used=self.format_name,
            rows=rows,
            warnings=[] if all_tables else ["Could not extract tables reliably from PDF."],
        )
