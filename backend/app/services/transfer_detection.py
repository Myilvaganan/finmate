"""Detects internal transfers, credit card payments, and cash withdrawals so they aren't
double-counted as income/expense in analytics."""
import re
from typing import Dict, List

from app.services.normalization import NormalizedTransaction

_CARD_PAYMENT_RE = re.compile(r"CREDIT CARD PAYMENT|CC PAYMENT|CARD BILL PAYMENT", re.I)
_CASH_WITHDRAWAL_RE = re.compile(r"\bATM\b|CASH WDL|CASH WITHDRAWAL", re.I)
_TRANSFER_RE = re.compile(r"\bUPI\b|\bNEFT\b|\bIMPS\b|\bRTGS\b|FUND TRANSFER", re.I)


def classify_transaction_type(txn: NormalizedTransaction, user_account_identifiers: List[str]) -> str:
    """Returns one of: income, expense, transfer, card_payment, cash_withdrawal."""
    text = txn.original_description.upper()

    if _CARD_PAYMENT_RE.search(text):
        return "card_payment"
    if _CASH_WITHDRAWAL_RE.search(text) and txn.debit > 0:
        return "cash_withdrawal"

    if _TRANSFER_RE.search(text):
        # If the description references another account the user owns, it's a pure internal transfer.
        if any(ident and ident in text for ident in user_account_identifiers):
            return "transfer"
        # UPI/NEFT to third parties is still commonly a transfer rather than a categorized expense/income;
        # categorization.py may still assign a specific category (e.g. rent paid via UPI).
        return "transfer" if txn.debit > 0 and txn.credit == 0 and _looks_like_p2p(text) else (
            "income" if txn.credit > 0 else "expense"
        )

    return "income" if txn.credit > 0 else "expense"


def _looks_like_p2p(text: str) -> bool:
    # Heuristic: UPI to a person (no merchant keyword) often reads like "UPI/JOHN DOE/..."
    return bool(re.match(r"^(UPI|NEFT|IMPS|RTGS)[-/]", text)) and not re.search(
        r"SWIGGY|ZOMATO|AMAZON|FLIPKART|NETFLIX", text
    )
