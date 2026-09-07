"""Validates that balance progresses consistently: prev_balance + credit - debit ~= current_balance."""
from dataclasses import dataclass
from typing import List, Optional

from app.services.normalization import NormalizedTransaction

ROUNDING_TOLERANCE = 1.0  # currency units


@dataclass
class BalanceMismatch:
    row_index: int
    date: object
    expected: float
    actual: float
    difference: float


def validate_balances(transactions: List[NormalizedTransaction]) -> List[BalanceMismatch]:
    mismatches: List[BalanceMismatch] = []
    ordered = sorted(
        [t for t in transactions if t.balance is not None],
        key=lambda t: (t.transaction_date, t.row_index),
    )
    if len(ordered) < 2:
        return mismatches

    prev = ordered[0]
    for txn in ordered[1:]:
        expected = prev.balance + txn.credit - txn.debit
        diff = round(expected - txn.balance, 2)
        if abs(diff) > ROUNDING_TOLERANCE:
            mismatches.append(
                BalanceMismatch(
                    row_index=txn.row_index, date=txn.transaction_date,
                    expected=round(expected, 2), actual=txn.balance, difference=diff,
                )
            )
        prev = txn
    return mismatches
