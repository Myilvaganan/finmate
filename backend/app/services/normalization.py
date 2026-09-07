"""Converts parser output (RawTransactionRow) into normalized transaction dicts.

Handles the many ways banks represent debit/credit, and never turns a transfer
into an expense by accident -- that classification is refined later by
transfer_detection.py once all rows for an account are known.
"""
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from app.parsers.base import RawTransactionRow
from app.services.merchant_normalization import normalize_description, normalize_merchant
from app.utils.dates import is_date_ambiguous, parse_transaction_date
from app.utils.fingerprint import transaction_fingerprint

_DEBIT_WORDS = {"debit", "dr", "withdrawal", "amount debited", "wd"}
_CREDIT_WORDS = {"credit", "cr", "deposit", "amount credited", "dep"}

_PAYMENT_METHOD_PATTERNS = [
    ("upi", re.compile(r"\bUPI\b", re.I)),
    ("card", re.compile(r"\bPOS\b|\bCARD\b|\bVISA\b|\bMASTERCARD\b", re.I)),
    ("netbanking", re.compile(r"NETBANKING|NEFT|RTGS|FUND TRF", re.I)),
    ("cheque", re.compile(r"\bCHQ\b|\bCHEQUE\b", re.I)),
    ("cash", re.compile(r"\bATM\b|\bCASH\b", re.I)),
]


@dataclass
class NormalizedTransaction:
    row_index: int
    transaction_date: Optional[object]
    value_date: Optional[object]
    date_ambiguous: bool
    original_description: str
    normalized_description: str
    merchant_name: str
    reference_number: str
    debit: float
    credit: float
    amount: float
    balance: Optional[float]
    payment_method: str
    fingerprint: str
    warnings: List[str]


def _to_float(raw: str) -> float:
    if not raw:
        return 0.0
    cleaned = re.sub(r"[^\d.\-]", "", raw.replace(",", ""))
    if not cleaned or cleaned in ("-", "."):
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _detect_payment_method(description: str) -> str:
    for method, pattern in _PAYMENT_METHOD_PATTERNS:
        if pattern.search(description):
            return method
    return "other"


def normalize_row(row: RawTransactionRow, account_id: str, currency: str) -> Optional[NormalizedTransaction]:
    warnings: List[str] = []
    txn_date = parse_transaction_date(row.transaction_date_raw)
    if txn_date is None:
        return None

    ambiguous = is_date_ambiguous(row.transaction_date_raw)
    if ambiguous:
        warnings.append(f"Row {row.row_index}: date '{row.transaction_date_raw}' is ambiguous; assumed DD/MM.")

    debit = 0.0
    credit = 0.0

    if row.debit_raw or row.credit_raw:
        debit = _to_float(row.debit_raw)
        credit = _to_float(row.credit_raw)
    elif row.amount_raw:
        amount_val = _to_float(row.amount_raw)
        type_hint = (row.type_raw or "").strip().lower()
        if type_hint in _DEBIT_WORDS or (not type_hint and amount_val < 0):
            debit = abs(amount_val)
        elif type_hint in _CREDIT_WORDS or (not type_hint and amount_val > 0):
            credit = abs(amount_val)
        else:
            # Unresolvable sign; default to expense but flag for review.
            debit = abs(amount_val)
            warnings.append(f"Row {row.row_index}: could not determine debit/credit; assumed debit.")

    normalized_desc = normalize_description(row.description_raw)
    merchant_name = normalize_merchant(row.description_raw)
    balance = _to_float(row.balance_raw) if row.balance_raw else None

    fingerprint = transaction_fingerprint(
        account_id=account_id,
        transaction_date=txn_date,
        normalized_description=normalized_desc,
        debit=debit,
        credit=credit,
        reference_number=row.reference_raw,
    )

    return NormalizedTransaction(
        row_index=row.row_index,
        transaction_date=txn_date,
        value_date=parse_transaction_date(row.value_date_raw) if row.value_date_raw else None,
        date_ambiguous=ambiguous,
        original_description=row.description_raw,
        normalized_description=normalized_desc,
        merchant_name=merchant_name,
        reference_number=row.reference_raw,
        debit=debit,
        credit=credit,
        amount=credit - debit,
        balance=balance,
        payment_method=_detect_payment_method(row.description_raw),
        fingerprint=fingerprint,
        warnings=warnings,
    )


def normalize_rows(rows: List[RawTransactionRow], account_id: str, currency: str) -> List[NormalizedTransaction]:
    result = []
    for row in rows:
        normalized = normalize_row(row, account_id, currency)
        if normalized is not None:
            result.append(normalized)
    return result
