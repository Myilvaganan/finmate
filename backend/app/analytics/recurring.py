"""Detects recurring transactions (subscriptions, EMIs, rent, utility/insurance bills) by
grouping same-merchant transactions and checking amount similarity + periodicity."""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import mean, median, pstdev
from typing import Dict, List, Optional

from app.models.transaction import Transaction

_SUBSCRIPTION_KEYWORDS = ("NETFLIX", "SPOTIFY", "PRIME", "HOTSTAR", "YOUTUBE", "ICLOUD", "GOOGLE ONE")
_LOAN_KEYWORDS = ("EMI", "LOAN")

# Only these category groups represent an actual recurring bill (rent, electricity/gas, EMI,
# insurance premium, subscription). Everything else (shopping, food, transfers, ...) can also
# repeat by coincidence but isn't a "recurring payment" the way a user means it.
_BILL_CATEGORY_GROUPS = {"Housing", "Utilities", "Insurance", "EMI / Loans", "Subscriptions"}
# Utility/insurance/rent bills fluctuate with usage from month to month -- a fixed-amount
# subscription or EMI shouldn't. Widen the amount-consistency tolerance only for the former.
_VARIABLE_AMOUNT_GROUPS = {"Housing", "Utilities", "Insurance"}


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
    category_name: Optional[str] = None
    is_loan: bool = False


def _infer_frequency(gaps_days: List[float]) -> Optional[str]:
    # Median is robust to a one-off gap (a skipped or doubled-up bill); a plain mean lets a
    # single outlier gap drag an otherwise-regular series out of range.
    gap = median(gaps_days)
    if pstdev(gaps_days) / gap > 0.5:
        return None  # gaps too irregular to call this a fixed schedule
    if 25 <= gap <= 35:
        return "monthly"
    if 6 <= gap <= 8:
        return "weekly"
    if 85 <= gap <= 100:
        return "quarterly"
    if 350 <= gap <= 380:
        return "yearly"
    return None


def detect_recurring(
    transactions: List[Transaction],
    merchant_names: Optional[Dict[str, str]] = None,
    category_names: Optional[Dict[str, str]] = None,
    category_parent_types: Optional[Dict[str, str]] = None,
    category_groups: Optional[Dict[str, str]] = None,
    as_of: Optional[date] = None,
) -> List[RecurringCandidate]:
    as_of = as_of or date.today()
    merchant_names = merchant_names or {}
    category_names = category_names or {}
    category_parent_types = category_parent_types or {}
    category_groups = category_groups or {}
    by_merchant: Dict[str, List[Transaction]] = defaultdict(list)
    for t in transactions:
        if t.debit <= 0 or not t.merchant_id:
            continue
        # Only look at the trailing ~13 months: a plan/price change or a mobile recharge from
        # years ago shouldn't drag today's amount-consistency or occurrence count off.
        if (as_of - t.transaction_date).days > 400:
            continue
        # Card bill payments, cash withdrawals, and P2P/P2M transfers repeat on a schedule too,
        # but they're money movement, not a recurring bill/subscription -- exclude them.
        if category_parent_types.get(t.category_id) == "transfer":
            continue
        # Restrict to categories that are actually bill-like (rent, utilities, EMI, insurance,
        # subscriptions). When no category grouping is supplied, fall back to only excluding
        # transfers so callers that don't pass it keep the old (broader) behavior.
        if category_groups and category_groups.get(t.category_id) not in _BILL_CATEGORY_GROUPS:
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
        group = category_groups.get(txns[-1].category_id)
        amount_tolerance = 0.75 if group in _VARIABLE_AMOUNT_GROUPS else 0.25
        if amount_std / avg_amount > amount_tolerance:
            continue  # amounts too inconsistent to be a recurring charge

        # Gaps use distinct calendar days rather than every row: two charges landing on the
        # same date (e.g. two EMIs from the same lender settling together) are one billing
        # event for periodicity purposes and shouldn't register as a zero-day gap.
        event_dates = sorted(set(t.transaction_date for t in txns))
        if len(event_dates) < 3:
            continue
        gaps = [(event_dates[i] - event_dates[i - 1]).days for i in range(1, len(event_dates))]
        frequency = _infer_frequency(gaps)
        if frequency is None:
            continue

        last = txns[-1]
        gap_map = {"weekly": 7, "monthly": 30, "quarterly": 91, "yearly": 365}
        if (as_of - last.transaction_date).days > gap_map[frequency] * 1.5:
            continue  # no charge in over 1.5 periods -- likely closed/cancelled, not still recurring
        next_expected = last.transaction_date + timedelta(days=gap_map[frequency])
        multiplier = {"weekly": 52, "monthly": 12, "quarterly": 4, "yearly": 1}[frequency]
        merchant_name = merchant_names.get(merchant_id, "Unknown")
        category_name = category_names.get(last.category_id) if last.category_id else None
        is_loan = bool(category_name and any(k in category_name.upper() for k in _LOAN_KEYWORDS))

        results.append(
            RecurringCandidate(
                merchant_name=merchant_name,
                merchant_id=merchant_id,
                average_amount=round(avg_amount, 2),
                frequency=frequency,
                occurrences=len(event_dates),
                last_charged_date=last.transaction_date,
                next_expected_date=next_expected,
                annualized_cost=round(avg_amount * multiplier, 2),
                is_subscription=any(k in last.original_description.upper() for k in _SUBSCRIPTION_KEYWORDS),
                category_name=category_name,
                is_loan=is_loan,
            )
        )
    return results
