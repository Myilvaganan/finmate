"""Detects recurring transactions (subscriptions, EMIs, rent) by grouping same-merchant
transactions and checking amount similarity + periodicity."""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import mean, pstdev
from typing import Dict, List, Optional

from app.models.transaction import Transaction

_SUBSCRIPTION_KEYWORDS = ("NETFLIX", "SPOTIFY", "PRIME", "HOTSTAR", "YOUTUBE", "ICLOUD", "GOOGLE ONE")


@dataclass
class RecurringCandidate:
    merchant_name: str
    merchant_id: Optional[str]
    average_amount: float
    frequency: str
    occurrences: int
    last_charged_date: date
    next_expected_date: date
    annualized_cost: float
    is_subscription: bool


def _infer_frequency(gaps_days: List[float]) -> Optional[str]:
    avg_gap = mean(gaps_days)
    if 25 <= avg_gap <= 35:
        return "monthly"
    if 6 <= avg_gap <= 8:
        return "weekly"
    if 85 <= avg_gap <= 100:
        return "quarterly"
    if 350 <= avg_gap <= 380:
        return "yearly"
    return None


def detect_recurring(
    transactions: List[Transaction], merchant_names: Optional[Dict[str, str]] = None
) -> List[RecurringCandidate]:
    merchant_names = merchant_names or {}
    by_merchant: Dict[str, List[Transaction]] = defaultdict(list)
    for t in transactions:
        if t.debit <= 0 or not t.merchant_id:
            continue
        by_merchant[t.merchant_id].append(t)

    results: List[RecurringCandidate] = []
    for merchant_id, txns in by_merchant.items():
        if len(txns) < 3:
            continue
        txns.sort(key=lambda t: t.transaction_date)
        amounts = [t.debit for t in txns]
        avg_amount = mean(amounts)
        if avg_amount == 0:
            continue
        amount_std = pstdev(amounts) if len(amounts) > 1 else 0
        if amount_std / avg_amount > 0.25:
            continue  # amounts too inconsistent to be a recurring charge

        gaps = [
            (txns[i].transaction_date - txns[i - 1].transaction_date).days for i in range(1, len(txns))
        ]
        frequency = _infer_frequency(gaps)
        if frequency is None:
            continue

        last = txns[-1]
        gap_map = {"weekly": 7, "monthly": 30, "quarterly": 91, "yearly": 365}
        next_expected = last.transaction_date + timedelta(days=gap_map[frequency])
        multiplier = {"weekly": 52, "monthly": 12, "quarterly": 4, "yearly": 1}[frequency]
        merchant_name = merchant_names.get(merchant_id, "Unknown")

        results.append(
            RecurringCandidate(
                merchant_name=merchant_name,
                merchant_id=merchant_id,
                average_amount=round(avg_amount, 2),
                frequency=frequency,
                occurrences=len(txns),
                last_charged_date=last.transaction_date,
                next_expected_date=next_expected,
                annualized_cost=round(avg_amount * multiplier, 2),
                is_subscription=any(k in last.original_description.upper() for k in _SUBSCRIPTION_KEYWORDS),
            )
        )
    return results
