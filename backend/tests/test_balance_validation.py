from app.parsers.base import RawTransactionRow
from app.services.balance_validation import validate_balances
from app.services.normalization import normalize_row


def _txn(row_index, date_str, desc, debit="", credit="", balance=""):
    row = RawTransactionRow(row_index=row_index, transaction_date_raw=date_str, description_raw=desc, debit_raw=debit, credit_raw=credit, balance_raw=balance)
    return normalize_row(row, "acc1", "INR")


def test_consistent_balances_produce_no_mismatch():
    txns = [
        _txn(0, "01/01/2026", "OPEN", credit="1000", balance="1000"),
        _txn(1, "02/01/2026", "SPEND", debit="200", balance="800"),
        _txn(2, "03/01/2026", "SPEND", debit="100", balance="700"),
    ]
    assert validate_balances(txns) == []


def test_mismatch_detected_beyond_tolerance():
    txns = [
        _txn(0, "01/01/2026", "OPEN", credit="1000", balance="1000"),
        _txn(1, "02/01/2026", "SPEND", debit="200", balance="750"),  # should be 800
    ]
    mismatches = validate_balances(txns)
    assert len(mismatches) == 1
    assert mismatches[0].difference == 50.0


def test_small_rounding_difference_is_tolerated():
    txns = [
        _txn(0, "01/01/2026", "OPEN", credit="1000", balance="1000"),
        _txn(1, "02/01/2026", "SPEND", debit="200.30", balance="799.90"),
    ]
    assert validate_balances(txns) == []
