"""Deterministic anomaly detection -- statistics only, no LLM involved. AI (see app/ai) may only
explain an anomaly already found here, never decide on its own that one exists."""
from dataclasses import dataclass
from datetime import date
from statistics import mean, pstdev
from typing import Dict, List, Optional

from dateutil.relativedelta import relativedelta

from app.analytics.engine import AnalyticsEngine

LARGE_TXN_MULTIPLIER = 3.0  # a transaction this many std-devs above the mean expense is "unusual"
CATEGORY_SPIKE_MULTIPLIER = 1.5  # current month vs trailing average
LOOKBACK_MONTHS = 6


@dataclass
class Anomaly:
    anomaly_type: str
    severity: str  # info | warning | critical
    confidence: float
    subject: str  # category/merchant name, or a transaction description
    baseline: float
    actual_value: float
    deviation_percent: Optional[float]
    explanation: str


def _severity(deviation_percent: Optional[float]) -> str:
    if deviation_percent is None:
        return "info"
    if deviation_percent >= 100:
        return "critical"
    if deviation_percent >= 50:
        return "warning"
    return "info"


def detect_category_spikes(engine: AnalyticsEngine, account_id: Optional[str], today: date) -> List[Anomaly]:
    """Compares this month's category spend against the trailing LOOKBACK_MONTHS average for
    that same category (excluding the current month) using a simple mean baseline."""
    this_month_start = today.replace(day=1)
    lookback_start = this_month_start - relativedelta(months=LOOKBACK_MONTHS)
    lookback_end = this_month_start - relativedelta(days=1)

    current = {c["category_id"]: c for c in engine.category_breakdown(account_id, this_month_start, today)}
    history_by_month: Dict[str, Dict] = {}
    cursor = lookback_start
    while cursor <= lookback_end:
        month_end = min(cursor + relativedelta(months=1) - relativedelta(days=1), lookback_end)
        for c in engine.category_breakdown(account_id, cursor, month_end):
            history_by_month.setdefault(c["category_id"], []).append(c["total"])
        cursor += relativedelta(months=1)

    anomalies = []
    for cid, entry in current.items():
        history = history_by_month.get(cid, [])
        if len(history) < 3:
            continue  # not enough history to trust a baseline
        baseline = mean(history)
        if baseline <= 0:
            continue
        actual = entry["total"]
        deviation_pct = round((actual - baseline) / baseline * 100, 1)
        if deviation_pct < (CATEGORY_SPIKE_MULTIPLIER - 1) * 100:
            continue
        anomalies.append(Anomaly(
            anomaly_type="category_spike", severity=_severity(deviation_pct), confidence=0.85,
            subject=entry["category"], baseline=round(baseline, 2), actual_value=actual,
            deviation_percent=deviation_pct,
            explanation=f"{entry['category']} spending is {deviation_pct}% above your recent average.",
        ))
    return anomalies


def detect_large_transactions(engine: AnalyticsEngine, account_id: Optional[str], start: date, end: date) -> List[Anomaly]:
    """Flags expenses that are LARGE_TXN_MULTIPLIER standard deviations above the mean expense
    for the period -- a merchant-agnostic outlier check, distinct from the flat-threshold
    "large transactions" list."""
    txns = engine.large_transactions(account_id, start, end, limit=1000)
    amounts = [t["amount"] for t in txns]
    if len(amounts) < 5:
        return []
    baseline = mean(amounts)
    spread = pstdev(amounts)
    if spread == 0:
        return []
    threshold = baseline + LARGE_TXN_MULTIPLIER * spread

    anomalies = []
    for t in txns:
        if t["amount"] <= threshold:
            continue
        deviation_pct = round((t["amount"] - baseline) / baseline * 100, 1) if baseline else None
        anomalies.append(Anomaly(
            anomaly_type="unusual_transaction", severity=_severity(deviation_pct), confidence=0.8,
            subject=t["description"] or "Unknown", baseline=round(baseline, 2), actual_value=t["amount"],
            deviation_percent=deviation_pct,
            explanation=f"This transaction is unusually large compared to your typical spending.",
        ))
    return anomalies


def detect_income_drop(engine: AnalyticsEngine, account_id: Optional[str], today: date) -> List[Anomaly]:
    this_month_start = today.replace(day=1)
    last_month_end = this_month_start - relativedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    current_income = engine.total_income(account_id, this_month_start, today)
    previous_income = engine.total_income(account_id, last_month_start, last_month_end)
    if previous_income <= 0:
        return []
    deviation_pct = round((current_income - previous_income) / previous_income * 100, 1)
    if deviation_pct > -25:
        return []
    return [Anomaly(
        anomaly_type="income_drop", severity=_severity(abs(deviation_pct)), confidence=0.9,
        subject="Income", baseline=previous_income, actual_value=current_income,
        deviation_percent=deviation_pct,
        explanation=f"Income this month is {abs(deviation_pct)}% lower than last month.",
    )]


def detect_anomalies(engine: AnalyticsEngine, account_id: Optional[str], today: date) -> List[Anomaly]:
    this_month_start = today.replace(day=1)
    anomalies: List[Anomaly] = []
    anomalies.extend(detect_category_spikes(engine, account_id, today))
    anomalies.extend(detect_large_transactions(engine, account_id, this_month_start, today))
    anomalies.extend(detect_income_drop(engine, account_id, today))
    # Most severe / most confident first so the UI can show only the top few.
    order = {"critical": 0, "warning": 1, "info": 2}
    anomalies.sort(key=lambda a: (order.get(a.severity, 3), -a.confidence))
    return anomalies
