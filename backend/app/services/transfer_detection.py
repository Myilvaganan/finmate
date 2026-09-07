"""Detects internal transfers, credit card payments, and cash withdrawals so they aren't
double-counted as income/expense in analytics."""
import re
from typing import Dict, List, Optional

from app.services.normalization import NormalizedTransaction

_CARD_PAYMENT_RE = re.compile(r"CREDIT CARD PAYMENT|CC PAYMENT|CARD BILL PAYMENT", re.I)
_CASH_WITHDRAWAL_RE = re.compile(r"\bATM\b|CASH WDL|CASH WITHDRAWAL", re.I)
_TRANSFER_RE = re.compile(r"\bUPI\b|\bNEFT\b|\bIMPS\b|\bRTGS\b|FUND TRANSFER", re.I)


_TWO_PARTY_RE = re.compile(r"\bTO\b")


def _account_holder_anchors(full_name: Optional[str]) -> List[str]:
    """Name fragments long enough to reliably identify the account holder in a bank-statement
    counterparty field, truncated to 6 chars since banks often cut names short to fit a field
    width (e.g. 'S MYILVAGANAN' shows up as 'S MYILVAG' or 'SMYILVAG')."""
    parts = [p for p in re.split(r"[\s.]+", (full_name or "").upper()) if len(p) >= 3]
    return [p[:6] for p in parts]


def _looks_like_self_transfer_credit(text: str, account_holder_name: Optional[str]) -> bool:
    """Credit-side only: a UPI/IMPS/RTGS/NEFT credit whose counterparty field is the account
    holder's own name (e.g. a P2A 'person to account' transfer between your own linked accounts)
    is a self-transfer, not income. Skips any '<sender> TO <recipient>' formatted description --
    those name both parties, so a same-name match there doesn't reliably mean *you* are both
    parties (e.g. 'RAZORPAY S TO S MYILVAGA' is a payment-gateway settlement, not a self-transfer).
    Deliberately not applied to debit-side descriptions: virtually every self-initiated UPI debit
    shows the payer's own name/VPA as a label regardless of who the money actually goes to, so the
    same check there would misclassify real expenses (bills, payments to other people) as transfers."""
    if _TWO_PARTY_RE.search(text):
        return False
    return any(anchor and anchor in text for anchor in _account_holder_anchors(account_holder_name))


def classify_transaction_type(
    txn: NormalizedTransaction, user_account_identifiers: List[str], account_holder_name: Optional[str] = None,
) -> str:
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
        if txn.debit > 0 and txn.credit == 0:
            # UPI/NEFT/IMPS to a third party still commonly reads like a transfer rather than a
            # categorized expense (rent split, family payment, etc.).
            return "transfer" if _looks_like_p2p(text) else "expense"
        if txn.credit > 0 and _looks_like_self_transfer_credit(text, account_holder_name):
            return "transfer"
        return "income" if txn.credit > 0 else "expense"

    return "income" if txn.credit > 0 else "expense"


def _looks_like_p2p(text: str) -> bool:
    # Heuristic: UPI to a person (no merchant keyword) often reads like "UPI/JOHN DOE/..."
    return bool(re.match(r"^(UPI|NEFT|IMPS|RTGS)[-/]", text)) and not re.search(
        r"SWIGGY|ZOMATO|AMAZON|FLIPKART|NETFLIX", text
    )
