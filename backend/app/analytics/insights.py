"""Deterministic insight detection. Produces structured insights grounded in analytics.engine
output; AI (see app/ai) may only rephrase these into natural language, never invent new ones."""
from dataclasses import dataclass
from datetime import date
from typing import List, Optional

from dateutil.relativedelta import relativedelta

from app.analytics.engine import AnalyticsEngine

EXPENSE_INCREASE_THRESHOLD_PCT = 15
SAVINGS_RATE_DROP_THRESHOLD_PCT = 5
LARGE_TRANSACTION_MULTIPLIER = 3


@dataclass
class SmartInsight:
    type: str
    title: str
    explanation: str
    supporting_metric: str
    severity: str  # info|warning|positive|critical
    confidence: float
    source_period: str


def generate_smart_insights(engine: AnalyticsEngine, account_id: Optional[str], today: date) -> List[SmartInsight]:
    insights: List[SmartInsight] = []

    this_month_start = today.replace(day=1)
    last_month_end = this_month_start - relativedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    this_month = engine.overview(account_id, this_month_start, today)
    last_month = engine.overview(account_id, last_month_start, last_month_end)

    if last_month.total_expenses > 0:
        change_pct = round(
            (this_month.total_expenses - last_month.total_expenses) / last_month.total_expenses * 100, 1
        )
        if change_pct >= EXPENSE_INCREASE_THRESHOLD_PCT:
            insights.append(
                SmartInsight(
                    type="expense_increase",
                    title="Spending increased compared with last month",
                    explanation=f"Your spending increased {change_pct}% compared with last month.",
                    supporting_metric=f"₹{this_month.total_expenses:,.0f} vs ₹{last_month.total_expenses:,.0f}",
                    severity="warning",
                    confidence=0.95,
                    source_period=f"{this_month_start.isoformat()} to {today.isoformat()}",
                )
            )
        elif change_pct <= -EXPENSE_INCREASE_THRESHOLD_PCT:
            insights.append(
                SmartInsight(
                    type="expense_decrease",
                    title="Spending decreased compared with last month",
                    explanation=f"Your spending decreased {abs(change_pct)}% compared with last month.",
                    supporting_metric=f"₹{this_month.total_expenses:,.0f} vs ₹{last_month.total_expenses:,.0f}",
                    severity="positive",
                    confidence=0.95,
                    source_period=f"{this_month_start.isoformat()} to {today.isoformat()}",
                )
            )

    if this_month.total_income > 0 and last_month.total_income > 0:
        rate_now = this_month.savings_rate
        rate_before = last_month.savings_rate
        if rate_now - rate_before >= SAVINGS_RATE_DROP_THRESHOLD_PCT:
            insights.append(
                SmartInsight(
                    type="savings_rate_improved",
                    title="Savings rate improved",
                    explanation=f"Your savings rate improved from {rate_before}% to {rate_now}%.",
                    supporting_metric=f"{rate_now}%",
                    severity="positive",
                    confidence=0.9,
                    source_period=f"{last_month_start.isoformat()} to {today.isoformat()}",
                )
            )
        elif rate_before - rate_now >= SAVINGS_RATE_DROP_THRESHOLD_PCT:
            insights.append(
                SmartInsight(
                    type="savings_rate_declined",
                    title="Savings rate declined",
                    explanation=f"Your savings rate declined from {rate_before}% to {rate_now}%.",
                    supporting_metric=f"{rate_now}%",
                    severity="warning",
                    confidence=0.9,
                    source_period=f"{last_month_start.isoformat()} to {today.isoformat()}",
                )
            )

    categories = engine.category_breakdown(account_id, this_month_start, today)
    if categories:
        top = categories[0]
        discretionary_categories = {"Shopping", "Entertainment", "Food & Dining", "Travel"}
        if top["category"] in discretionary_categories:
            insights.append(
                SmartInsight(
                    type="top_discretionary_category",
                    title=f"{top['category']} is your largest discretionary category",
                    explanation=f"{top['category']} accounted for ₹{top['total']:,.0f} this month.",
                    supporting_metric=f"₹{top['total']:,.0f}",
                    severity="info",
                    confidence=0.85,
                    source_period=f"{this_month_start.isoformat()} to {today.isoformat()}",
                )
            )

    return insights
