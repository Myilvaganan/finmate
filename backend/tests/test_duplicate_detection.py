from datetime import date

from app.parsers.base import RawTransactionRow
from app.services.duplicate_detection import DuplicateConfidence, ExistingTxnRef, check_duplicate
from app.services.normalization import normalize_row


def _txn(row_index, date_str, desc, debit="", credit=""):
    row = RawTransactionRow(row_index=row_index, transaction_date_raw=date_str, description_raw=desc, debit_raw=debit, credit_raw=credit)
    return normalize_row(row, account_id="acc1", currency="INR")


def test_exact_fingerprint_match_is_exact_duplicate():
    candidate = _txn(0, "15/01/2026", "SWIGGY ORDER 123", debit="450")
    existing = [ExistingTxnRef("t1", candidate.fingerprint, candidate.transaction_date, candidate.amount, candidate.normalized_description)]
    match = check_duplicate(candidate, existing)
    assert match.confidence == DuplicateConfidence.EXACT


def test_similar_transaction_within_days_is_likely_duplicate():
    candidate = _txn(0, "15/01/2026", "SWIGGY ORDER 123", debit="450.00")
    existing = [ExistingTxnRef("t1", "different-fingerprint", date(2026, 1, 16), -450.00, "SWIGGY ORDER 123")]
    match = check_duplicate(candidate, existing)
    assert match.confidence in (DuplicateConfidence.LIKELY, DuplicateConfidence.POSSIBLE)


def test_unrelated_transaction_is_not_duplicate():
    candidate = _txn(0, "15/01/2026", "SWIGGY ORDER 123", debit="450.00")
    existing = [ExistingTxnRef("t1", "other-fp", date(2026, 3, 1), -900.00, "AMAZON PURCHASE")]
    match = check_duplicate(candidate, existing)
    assert match.confidence == DuplicateConfidence.NONE
