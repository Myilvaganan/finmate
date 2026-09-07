import re
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import pandas as pd
import pdfplumber
from pdfminer.pdfdocument import PDFPasswordIncorrect

from app.parsers.base import BaseStatementParser, NormalizedStatement
from app.parsers.bank_detection import (
    detect_bank_from_columns, detect_bank_from_text, detect_account_type,
    detect_currency, detect_account_identifier,
)
from app.parsers.tabular import dataframe_to_rows
from app.parsers.pdf_line_fallback import extract_rows_from_text
from app.core.errors import AppError, ErrorCode
from app.core.logging import get_logger

logger = get_logger(__name__)

PERIOD_RE = re.compile(
    r"(?:statement period|for the period|period)\s*[:\-]?\s*"
    r"(\d{1,2}[/\-][A-Za-z0-9]{2,4}[/\-]\d{2,4})\s*(?:to|-|–)\s*(\d{1,2}[/\-][A-Za-z0-9]{2,4}[/\-]\d{2,4})",
    re.I,
)

# Some PDF fonts encode tab/space glyphs as unmapped character codes, which pdfplumber/pdfminer
# render as literal "(cid:N)" text -- strip these before any text or column-name matching.
_CID_ARTIFACT_RE = re.compile(r"\(cid:\d+\)")

_HEADER_DATE_HINTS = ("date",)
_HEADER_BALANCE_HINTS = ("balance",)


def _clean_cell(text: Optional[str]) -> str:
    """For table cell values: safe to collapse all whitespace, including internal newlines."""
    if not text:
        return ""
    text = _CID_ARTIFACT_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_page_text(text: Optional[str]) -> str:
    """For full-page text: strips cid artifacts but preserves line breaks, since the line-based
    fallback parser (pdf_line_fallback.py) depends on each transaction being its own line."""
    if not text:
        return ""
    text = _CID_ARTIFACT_RE.sub(" ", text)
    return re.sub(r"[ \t]+", " ", text)


def _looks_like_header_row(row: List[Optional[str]]) -> bool:
    cells = [_clean_cell(c).lower() for c in row]
    has_date = any(any(h in c for h in _HEADER_DATE_HINTS) for c in cells)
    has_balance = any(any(h in c for h in _HEADER_BALANCE_HINTS) for c in cells)
    return has_date and has_balance


def _dedupe_columns(header: List[str]) -> List[str]:
    seen: Dict[str, int] = {}
    result = []
    for i, col in enumerate(header):
        name = col or f"col_{i}"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        result.append(name)
    return result


def _extract_transaction_tables(pdf) -> Tuple[List[pd.DataFrame], str]:
    """Scans every table on every page for a real transaction header (a row containing both a
    date-like and a balance-like column), skipping account-summary/legend tables entirely, and
    only concatenates tables that share the same header -- avoids corrupting one bank's table
    with an unrelated one, and avoids pandas failing on mismatched/duplicate column sets."""
    groups: Dict[Tuple[str, ...], List[pd.DataFrame]] = defaultdict(list)
    full_text = ""
    # Multi-page statements typically print the header once and never repeat it on continuation
    # pages -- track the last recognized header so those pages aren't silently dropped.
    current_header: Optional[List[str]] = None

    for page in pdf.pages:
        full_text += _clean_page_text(page.extract_text()) + "\n"
        for raw_table in page.extract_tables():
            if not raw_table:
                continue
            cleaned_table = [[_clean_cell(cell) for cell in row] for row in raw_table]

            header_idx = None
            for i, row in enumerate(cleaned_table[:5]):
                if _looks_like_header_row(row):
                    header_idx = i
                    break

            if header_idx is not None and header_idx < len(cleaned_table) - 1:
                header = _dedupe_columns(cleaned_table[header_idx])
                body = cleaned_table[header_idx + 1:]
                current_header = header
            elif (
                header_idx is None
                and current_header is not None
                and len(cleaned_table[0]) == len(current_header)
            ):
                # No header on this table (continuation page) but the column count matches the
                # last recognized transaction table -- treat every row as body under that header.
                header = current_header
                body = cleaned_table
            else:
                continue

            if not body:
                continue
            df = pd.DataFrame(body, columns=header)
            signature = tuple(c.lower() for c in header)
            groups[signature].append(df)

    if not groups:
        return [], full_text

    best_signature = max(groups, key=lambda sig: sum(len(df) for df in groups[sig]))
    return groups[best_signature], full_text


class PDFStatementParser(BaseStatementParser):
    format_name = "pdf"

    def can_parse(self, filename: str, sample: bytes) -> bool:
        return filename.lower().endswith(".pdf") or sample.startswith(b"%PDF")

    def parse(self, file_path: str, password: Optional[str] = None) -> NormalizedStatement:
        try:
            with pdfplumber.open(file_path, password=password or "") as pdf:
                all_tables, full_text = _extract_transaction_tables(pdf)
        except PDFPasswordIncorrect:
            if password:
                raise AppError(ErrorCode.PDF_PASSWORD_INCORRECT, "The password provided is incorrect.")
            raise AppError(ErrorCode.PDF_PASSWORD_REQUIRED, "This PDF is password protected. Please provide the password.")
        except Exception as exc:
            raise AppError(ErrorCode.PARSER_FAILED, f"Could not parse PDF file: {exc}")

        df = pd.DataFrame()
        rows: List = []
        if all_tables:
            df = pd.concat(all_tables, ignore_index=True).astype(str)
            rows = dataframe_to_rows(df)

        fallback_used = False
        if not rows:
            rows = extract_rows_from_text(full_text)
            fallback_used = bool(rows)

        if not rows:
            if all_tables:
                detected_columns = list(df.columns)
                logger.warning("PDF table found but no rows recognized. Detected columns: %s", detected_columns)
                raise AppError(
                    ErrorCode.NO_TRANSACTIONS_FOUND,
                    "Found a table in this PDF, but couldn't recognize its date/description/amount columns "
                    f"(columns detected: {', '.join(detected_columns)}). This bank's layout may not be supported yet.",
                    details={"detected_columns": detected_columns},
                )
            raise AppError(
                ErrorCode.NO_TRANSACTIONS_FOUND,
                "No transaction tables found in PDF. It may be a scanned image — try OCR upload.",
            )

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
            warnings=(
                ["This statement's layout required a text-based fallback to extract transactions. "
                 "Please review the imported data carefully before confirming."]
                if fallback_used else []
            ),
        )
