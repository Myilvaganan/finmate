"""Shared column-detection logic for CSV/Excel/HTML/generic tabular statements."""
import re
from typing import Dict, List, Optional

import pandas as pd

from app.parsers.base import RawTransactionRow

_DATE_COLS = ["date", "transaction date", "txn date", "value date", "posting date"]
_DESC_COLS = ["description", "narration", "particulars", "transaction remarks", "details", "remarks"]
_DEBIT_COLS = ["debit", "withdrawal amt", "withdrawal amt.", "withdrawal", "dr", "debit amount"]
_CREDIT_COLS = ["credit", "deposit amt", "deposit amt.", "deposit", "cr", "credit amount"]
_AMOUNT_COLS = ["amount", "transaction amount"]
_TYPE_COLS = ["type", "transaction type", "dr/cr", "cr/dr"]
_BALANCE_COLS = ["balance", "closing balance", "available balance"]
_REF_COLS = ["reference", "ref no", "reference number", "chq no", "chq./ref.no.", "cheque no"]


def _find_column(columns: List[str], candidates: List[str]) -> Optional[str]:
    normalized = {c.strip().lower(): c for c in columns}
    for cand in candidates:
        if cand in normalized:
            return normalized[cand]
    for norm, orig in normalized.items():
        for cand in candidates:
            if cand in norm:
                return orig
    return None


def detect_column_map(columns: List[str]) -> Dict[str, Optional[str]]:
    return {
        "date": _find_column(columns, _DATE_COLS),
        "description": _find_column(columns, _DESC_COLS),
        "debit": _find_column(columns, _DEBIT_COLS),
        "credit": _find_column(columns, _CREDIT_COLS),
        "amount": _find_column(columns, _AMOUNT_COLS),
        "type": _find_column(columns, _TYPE_COLS),
        "balance": _find_column(columns, _BALANCE_COLS),
        "reference": _find_column(columns, _REF_COLS),
    }


_SUMMARY_MARKER_RE = re.compile(
    r"^(opening|closing)\s+balance\b|^(transaction\s+)?total\b|^b/f\b|^brought\s+forward\b", re.I
)


def dataframe_to_rows(df: pd.DataFrame) -> List[RawTransactionRow]:
    col_map = detect_column_map(list(df.columns))
    rows: List[RawTransactionRow] = []

    def cell(row, key) -> str:
        col = col_map.get(key)
        if not col or col not in row:
            return ""
        val = row[col]
        if pd.isna(val):
            return ""
        return str(val).strip()

    for idx, row in df.iterrows():
        date_raw = cell(row, "date")
        desc_raw = cell(row, "description")
        if not date_raw and not desc_raw:
            continue
        # Opening/closing-balance and running-total marker rows aren't real transactions --
        # they often land in the date/amount columns and can otherwise fool fuzzy date parsing
        # into hallucinating a bogus transaction date from the balance figure.
        if _SUMMARY_MARKER_RE.match(date_raw) or _SUMMARY_MARKER_RE.match(desc_raw):
            continue
        rows.append(
            RawTransactionRow(
                row_index=int(idx),
                transaction_date_raw=date_raw,
                description_raw=desc_raw,
                debit_raw=cell(row, "debit"),
                credit_raw=cell(row, "credit"),
                amount_raw=cell(row, "amount"),
                type_raw=cell(row, "type"),
                balance_raw=cell(row, "balance"),
                reference_raw=cell(row, "reference"),
            )
        )
    return rows
