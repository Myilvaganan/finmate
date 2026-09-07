"""Structural bank detection: uses column names and text patterns, not just bank name strings."""
import re
from typing import List

KNOWN_BANKS = [
    "ICICI Bank", "Axis Bank", "HDFC Bank", "SBI", "Kotak Mahindra Bank",
    "IndusInd Bank", "Yes Bank", "IDFC FIRST Bank",
]

_BANK_SIGNATURES = {
    "ICICI Bank": [r"icici", r"icicibank"],
    "Axis Bank": [r"axis bank", r"axisbank"],
    "HDFC Bank": [r"hdfc bank", r"hdfcbank"],
    "SBI": [r"state bank of india", r"\bsbi\b"],
    "Kotak Mahindra Bank": [r"kotak mahindra", r"kotak bank"],
    "IndusInd Bank": [r"indusind"],
    "Yes Bank": [r"yes bank"],
    "IDFC FIRST Bank": [r"idfc first", r"idfc bank"],
}

# Column-name signatures used when bank name text isn't present (structural detection).
_COLUMN_SIGNATURES = {
    "ICICI Bank": {"transaction remarks", "withdrawal amt", "deposit amt"},
    "Axis Bank": {"particulars", "chq no", "tran date", "debit", "credit", "withdrawal amt.", "deposit amt."},
    "HDFC Bank": {"narration", "chq./ref.no.", "withdrawal amt.", "deposit amt."},
    "SBI": {"description", "debit", "credit", "balance"},
}

# IFSC code prefixes are the most reliable signal available: unlike free text, they can't be
# confused with a counterparty bank mentioned inside a UPI transaction reference.
_IFSC_PREFIX_TO_BANK = {
    "ICIC": "ICICI Bank", "UTIB": "Axis Bank", "HDFC": "HDFC Bank", "SBIN": "SBI",
    "KKBK": "Kotak Mahindra Bank", "INDB": "IndusInd Bank", "YESB": "Yes Bank", "IDFB": "IDFC FIRST Bank",
}
_IFSC_RE = re.compile(r"\b([A-Z]{4})0[A-Z0-9]{6}\b")

# Free-text bank-name search is only safe over a small header window (e.g. the first page) --
# scanning the whole statement risks matching a counterparty's bank name inside a transaction
# description (e.g. a UPI payment "via ICICI Ban[k]") and misattributing the entire statement.
_TEXT_SEARCH_WINDOW = 2000


def detect_bank_from_text(text: str) -> str:
    text = text or ""
    ifsc_match = _IFSC_RE.search(text[:_TEXT_SEARCH_WINDOW])
    if ifsc_match and ifsc_match.group(1) in _IFSC_PREFIX_TO_BANK:
        return _IFSC_PREFIX_TO_BANK[ifsc_match.group(1)]

    lower = text[:_TEXT_SEARCH_WINDOW].lower()
    for bank, patterns in _BANK_SIGNATURES.items():
        if any(re.search(p, lower) for p in patterns):
            return bank
    return "Other"


def detect_bank_from_columns(columns: List[str]) -> str:
    normalized = {c.strip().lower() for c in columns}
    best_bank, best_overlap = "Other", 0
    for bank, sig_cols in _COLUMN_SIGNATURES.items():
        overlap = len(normalized & sig_cols)
        if overlap > best_overlap:
            best_bank, best_overlap = bank, overlap
    return best_bank if best_overlap >= 2 else "Other"


def detect_account_type(text: str) -> str:
    lower = (text or "").lower()
    if "credit card" in lower or "card statement" in lower:
        return "credit_card"
    if "savings" in lower:
        return "bank"
    if "current account" in lower:
        return "bank"
    return "bank"


def detect_currency(text: str) -> str:
    if "₹" in (text or "") or "INR" in (text or "").upper():
        return "INR"
    if "$" in (text or "") or "USD" in (text or "").upper():
        return "USD"
    return "INR"


ACCOUNT_NUMBER_RE = re.compile(r"(?:a/?c\.?\s*no\.?|account\s*(?:number|no)\.?)\s*[:\-]?\s*([X\d]{4,20})", re.I)


def detect_account_identifier(text: str) -> str:
    match = ACCOUNT_NUMBER_RE.search(text or "")
    if match:
        digits = match.group(1)
        return mask_account_number(digits)
    return ""


def mask_account_number(number: str) -> str:
    digits = re.sub(r"\D", "", number)
    if len(digits) < 4:
        return "XXXX"
    return f"XXXX XXXX {digits[-4:]}"
