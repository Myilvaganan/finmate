"""Deterministic financial analytics engine. All dashboard/report numbers originate here via
SQL aggregation -- never from an LLM. See app/ai/tools.py for the AI-facing wrappers."""
from dataclasses import dataclass
from datetime import date
from statistics import median
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.analytics.date_ranges import (
    compare, enumerate_days, enumerate_months, month_key, previous_equivalent_period,
)
from app.models.transaction import Transaction
from app.models.category import Category, Merchant

INCLUDED_EXPENSE_TYPES = ("expense",)
INCLUDED_INCOME_TYPES = ("income",)
EXCLUDED_FROM_CASHFLOW = ("transfer", "card_payment")


def _base_query(db: Session, user_id: str, account_id: Optional[str], start: Optional[date], end: Optional[date]):
    q = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.is_excluded == False,  # noqa: E712
        Transaction.is_duplicate == False,  # noqa: E712
    )
    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    if start:
        q = q.filter(Transaction.transaction_date >= start)
    if end:
        q = q.filter(Transaction.transaction_date <= end)
    return q


@dataclass
class OverviewMetrics:
    total_income: float
    total_expenses: float
    net_cash_flow: float
    savings_rate: float
    transaction_count: int
    average_daily_expenses: float
    median_transaction: float
    largest_transaction: float
    smallest_transaction: float


class AnalyticsEngine:
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id

    def _sum(self, account_id, start, end, transaction_types, amount_field) -> float:
        q = _base_query(self.db, self.user_id, account_id, start, end).filter(
            Transaction.transaction_type.in_(transaction_types)
        )
        total = q.with_entities(func.sum(amount_field)).scalar()
        return round(total or 0.0, 2)

    def total_income(self, account_id=None, start=None, end=None) -> float:
        return self._sum(account_id, start, end, INCLUDED_INCOME_TYPES, Transaction.credit)

    def total_expenses(self, account_id=None, start=None, end=None) -> float:
        return self._sum(account_id, start, end, INCLUDED_EXPENSE_TYPES, Transaction.debit)

    def net_cash_flow(self, account_id=None, start=None, end=None) -> float:
        return round(self.total_income(account_id, start, end) - self.total_expenses(account_id, start, end), 2)

    def savings_rate(self, account_id=None, start=None, end=None) -> float:
        income = self.total_income(account_id, start, end)
        if income <= 0:
            return 0.0
        return round((income - self.total_expenses(account_id, start, end)) / income * 100, 2)

    def transaction_count(self, account_id=None, start=None, end=None) -> int:
        return _base_query(self.db, self.user_id, account_id, start, end).count()

    def overview(self, account_id=None, start=None, end=None) -> OverviewMetrics:
        expenses_q = _base_query(self.db, self.user_id, account_id, start, end).filter(
            Transaction.transaction_type.in_(INCLUDED_EXPENSE_TYPES)
        )
        amounts = [t.debit for t in expenses_q.all()]
        days = max(1, ((end or date.today()) - start).days) if start else 1

        all_txns = _base_query(self.db, self.user_id, account_id, start, end).all()
        signed_amounts = [t.amount for t in all_txns if t.transaction_type not in EXCLUDED_FROM_CASHFLOW]

        return OverviewMetrics(
            total_income=self.total_income(account_id, start, end),
            total_expenses=self.total_expenses(account_id, start, end),
            net_cash_flow=self.net_cash_flow(account_id, start, end),
            savings_rate=self.savings_rate(account_id, start, end),
            transaction_count=self.transaction_count(account_id, start, end),
            average_daily_expenses=round(sum(amounts) / days, 2) if amounts else 0.0,
            median_transaction=round(median(signed_amounts), 2) if signed_amounts else 0.0,
            largest_transaction=round(max(signed_amounts), 2) if signed_amounts else 0.0,
            smallest_transaction=round(min(signed_amounts), 2) if signed_amounts else 0.0,
        )

    def category_breakdown(self, account_id=None, start=None, end=None, compare_previous: bool = False) -> List[Dict]:
        q = (
            _base_query(self.db, self.user_id, account_id, start, end)
            .filter(Transaction.transaction_type.in_(INCLUDED_EXPENSE_TYPES))
            .join(Category, Transaction.category_id == Category.id, isouter=True)
            .with_entities(
                Category.id, Category.name, func.sum(Transaction.debit).label("total"), func.count(Transaction.id)
            )
            .group_by(Category.id)
            .order_by(func.sum(Transaction.debit).desc())
        )
        rows = q.all()
        total_expenses = sum(round(total or 0, 2) for _, _, total, _ in rows)

        prev_by_category: Dict[Optional[str], float] = {}
        if compare_previous and start and end:
            prev_start, prev_end = previous_equivalent_period(start, end)
            for entry in self.category_breakdown(account_id, prev_start, prev_end):
                prev_by_category[entry["category_id"]] = entry["total"]

        result = []
        for cid, name, total, count in rows:
            total = round(total or 0, 2)
            entry = {
                "category_id": cid, "category": name or "Uncategorized", "total": total, "count": count,
                "percentage": round(total / total_expenses * 100, 2) if total_expenses else 0.0,
            }
            if compare_previous and start and end:
                cmp = compare(total, prev_by_category.get(cid, 0.0))
                entry["previous_period_amount"] = cmp.previous
                entry["change_percent"] = cmp.change_percent
            result.append(entry)
        return result

    def merchant_ranking(
        self, account_id=None, start=None, end=None, limit: int = 10, compare_previous: bool = False
    ) -> List[Dict]:
        q = (
            _base_query(self.db, self.user_id, account_id, start, end)
            .filter(Transaction.transaction_type.in_(INCLUDED_EXPENSE_TYPES))
            .join(Merchant, Transaction.merchant_id == Merchant.id, isouter=True)
            .with_entities(
                Merchant.id, Merchant.display_name, func.sum(Transaction.debit).label("total"),
                func.count(Transaction.id),
            )
            .group_by(Merchant.id)
            .order_by(func.sum(Transaction.debit).desc())
            .limit(limit)
        )
        rows = q.all()
        total_expenses = self.total_expenses(account_id, start, end)

        prev_by_merchant: Dict[Optional[str], float] = {}
        if compare_previous and start and end:
            prev_start, prev_end = previous_equivalent_period(start, end)
            for entry in self.merchant_ranking(account_id, prev_start, prev_end, limit=10_000):
                prev_by_merchant[entry["merchant_id"]] = entry["total"]

        result = []
        for mid, name, total, count in rows:
            total = round(total or 0, 2)
            entry = {
                "merchant_id": mid, "merchant": name or "Unknown", "total": total, "count": count,
                "average_transaction": round(total / count, 2) if count else 0.0,
                "percentage_of_expenses": round(total / total_expenses * 100, 2) if total_expenses else 0.0,
            }
            if compare_previous and start and end:
                cmp = compare(total, prev_by_merchant.get(mid, 0.0))
                entry["previous_period_amount"] = cmp.previous
                entry["change_percent"] = cmp.change_percent
            result.append(entry)
        return result

    def category_trend(self, category_ids: List[str], account_id=None, start=None, end=None) -> Dict[str, List[Dict]]:
        """Monthly spend for a hand-picked set of categories -- powers the multi-line
        Category Spending Trend chart. Returns one zero-filled series per category id."""
        months = enumerate_months(start, end) if start and end else []
        q = (
            _base_query(self.db, self.user_id, account_id, start, end)
            .filter(Transaction.transaction_type.in_(INCLUDED_EXPENSE_TYPES), Transaction.category_id.in_(category_ids))
            .with_entities(Transaction.category_id, Transaction.transaction_date, Transaction.debit)
        )
        buckets: Dict[str, Dict[str, float]] = {cid: {} for cid in category_ids}
        for cid, txn_date, debit in q.all():
            buckets[cid][month_key(txn_date)] = buckets[cid].get(month_key(txn_date), 0.0) + (debit or 0.0)

        names = {c.id: c.name for c in self.db.query(Category).filter(Category.id.in_(category_ids)).all()}
        series = {}
        for cid in category_ids:
            if months:
                points = [
                    {"month": month_key(m), "amount": round(buckets[cid].get(month_key(m), 0.0), 2)}
                    for m in months
                ]
            else:
                points = [{"month": k, "amount": round(v, 2)} for k, v in sorted(buckets[cid].items())]
            series[cid] = {"category": names.get(cid, "Uncategorized"), "points": points}
        return series

    def fixed_vs_variable(self, account_id=None, start=None, end=None) -> Dict[str, float]:
        """Fixed = merchants whose payments already look recurring (rent/EMI/subscriptions/
        utilities all show up here) -- everything else is variable. No manual tagging required."""
        from app.analytics.recurring import detect_recurring
        all_txns = _base_query(self.db, self.user_id, account_id, None, None).all()
        merchant_names = {m.id: m.display_name for m in self.db.query(Merchant).all()}
        category_parent_types = {c.id: c.parent_type for c in self.db.query(Category).all()}
        fixed_merchant_ids = {
            c.merchant_id
            for c in detect_recurring(
                all_txns, merchant_names, category_parent_types=category_parent_types, as_of=end,
            )
            if c.merchant_id
        }

        rows = (
            _base_query(self.db, self.user_id, account_id, start, end)
            .filter(Transaction.transaction_type.in_(INCLUDED_EXPENSE_TYPES))
            .with_entities(Transaction.merchant_id, Transaction.debit)
            .all()
        )
        result = {"fixed": 0.0, "variable": 0.0}
        for merchant_id, debit in rows:
            key = "fixed" if merchant_id in fixed_merchant_ids else "variable"
            result[key] += debit or 0.0
        return {k: round(v, 2) for k, v in result.items()}

    def account_balance_trend(self, account_id=None, start=None, end=None) -> List[Dict]:
        """Per-account closing balance after each transaction date -- the account's own running
        balance column, not a cross-account sum (bank and credit-card balances mean different
        things and are never combined here)."""
        from app.models.account import Account
        accounts_q = self.db.query(Account).filter(Account.user_id == self.user_id)
        if account_id:
            accounts_q = accounts_q.filter(Account.id == account_id)

        result = []
        for account in accounts_q.all():
            q = (
                _base_query(self.db, account.user_id, account.id, start, end)
                .filter(Transaction.balance.isnot(None))
                .with_entities(Transaction.transaction_date, Transaction.balance)
                .order_by(Transaction.transaction_date, Transaction.created_at)
            )
            points = [{"date": d.isoformat(), "balance": round(b, 2)} for d, b in q.all()]
            result.append({
                "account_id": account.id, "bank_name": account.bank_name,
                "account_type": account.account_type, "currency": account.currency, "points": points,
            })
        return result

    def spending_heatmap(self, year: int, account_id=None) -> List[Dict]:
        """Daily expense totals for a full calendar year, zero-filled -- powers the calendar
        heatmap. One year at a time keeps the payload small even for heavy users."""
        start, end = date(year, 1, 1), date(year, 12, 31)
        totals = {
            d: round(t or 0, 2)
            for d, t in (
                _base_query(self.db, self.user_id, account_id, start, end)
                .filter(Transaction.transaction_type.in_(INCLUDED_EXPENSE_TYPES))
                .with_entities(Transaction.transaction_date, func.sum(Transaction.debit))
                .group_by(Transaction.transaction_date)
                .all()
            )
        }
        counts = {
            d: c
            for d, c in (
                _base_query(self.db, self.user_id, account_id, start, end)
                .filter(Transaction.transaction_type.in_(INCLUDED_EXPENSE_TYPES))
                .with_entities(Transaction.transaction_date, func.count(Transaction.id))
                .group_by(Transaction.transaction_date)
                .all()
            )
        }
        return [
            {"date": d.isoformat(), "amount": totals.get(d, 0.0), "transaction_count": counts.get(d, 0)}
            for d in enumerate_days(start, end)
        ]

    def daily_spending(self, account_id=None, start=None, end=None) -> List[Dict]:
        q = (
            _base_query(self.db, self.user_id, account_id, start, end)
            .filter(Transaction.transaction_type.in_(INCLUDED_EXPENSE_TYPES))
            .with_entities(Transaction.transaction_date, func.sum(Transaction.debit))
            .group_by(Transaction.transaction_date)
            .order_by(Transaction.transaction_date)
        )
        totals = {d: round(t or 0, 2) for d, t in q.all()}
        if not start or not end:
            return [{"date": d.isoformat(), "total": t} for d, t in sorted(totals.items())]
        # Zero-spending days are kept, not omitted, so charts show real gaps rather than
        # compressing the axis to only the days something happened.
        return [{"date": d.isoformat(), "total": totals.get(d, 0.0)} for d in enumerate_days(start, end)]

    def monthly_series(self, account_id=None, start=None, end=None) -> List[Dict]:
        rows = _base_query(self.db, self.user_id, account_id, start, end).all()
        buckets: Dict[str, Dict[str, float]] = {}
        for t in rows:
            key = month_key(t.transaction_date)
            b = buckets.setdefault(key, {"income": 0.0, "expenses": 0.0})
            if t.transaction_type == "income":
                b["income"] += t.credit
            elif t.transaction_type == "expense":
                b["expenses"] += t.debit
        if not start or not end:
            return [
                {"month": k, "income": round(v["income"], 2), "expenses": round(v["expenses"], 2)}
                for k, v in sorted(buckets.items())
            ]
        return [
            {
                "month": month_key(m),
                "income": round(buckets.get(month_key(m), {}).get("income", 0.0), 2),
                "expenses": round(buckets.get(month_key(m), {}).get("expenses", 0.0), 2),
            }
            for m in enumerate_months(start, end)
        ]

    def cashflow_series(self, account_id=None, start=None, end=None) -> List[Dict]:
        """Net cash flow and running cumulative cash flow, one point per month -- powers the
        Cash Flow Trend chart. Cumulative is a plain running sum over the chosen range, not a
        running account balance (transfers/exclusions already stripped out by _base_query)."""
        cumulative = 0.0
        result = []
        for row in self.monthly_series(account_id, start, end):
            net = round(row["income"] - row["expenses"], 2)
            cumulative = round(cumulative + net, 2)
            result.append({**row, "net_cash_flow": net, "cumulative_cash_flow": cumulative})
        return result

    def savings_rate_series(self, account_id=None, start=None, end=None) -> List[Dict]:
        result = []
        for row in self.monthly_series(account_id, start, end):
            income, expenses = row["income"], row["expenses"]
            rate = round((income - expenses) / income * 100, 2) if income > 0 else None
            result.append({"month": row["month"], "savings_rate": rate})
        return result

    def essential_vs_discretionary(self, account_id=None, start=None, end=None) -> Dict[str, float]:
        q = (
            _base_query(self.db, self.user_id, account_id, start, end)
            .filter(Transaction.transaction_type.in_(INCLUDED_EXPENSE_TYPES))
            .join(Category, Transaction.category_id == Category.id, isouter=True)
            .with_entities(Category.is_essential, func.sum(Transaction.debit))
            .group_by(Category.is_essential)
        )
        result = {"essential": 0.0, "discretionary": 0.0}
        for is_essential, total in q.all():
            key = "essential" if is_essential else "discretionary"
            result[key] += round(total or 0, 2)
        return result

    def payment_method_breakdown(self, account_id=None, start=None, end=None) -> List[Dict]:
        q = (
            _base_query(self.db, self.user_id, account_id, start, end)
            .filter(Transaction.transaction_type.in_(INCLUDED_EXPENSE_TYPES))
            .with_entities(Transaction.payment_method, func.sum(Transaction.debit))
            .group_by(Transaction.payment_method)
        )
        return [{"method": m, "total": round(t or 0, 2)} for m, t in q.all()]

    def account_balances(self) -> List[Dict]:
        from app.models.account import Account
        accounts = self.db.query(Account).filter(Account.user_id == self.user_id).all()
        return [
            {"account_id": a.id, "bank_name": a.bank_name, "balance": a.closing_balance, "currency": a.currency}
            for a in accounts
        ]

    def weekday_vs_weekend(self, account_id=None, start=None, end=None) -> Dict[str, float]:
        rows = (
            _base_query(self.db, self.user_id, account_id, start, end)
            .filter(Transaction.transaction_type.in_(INCLUDED_EXPENSE_TYPES))
            .with_entities(Transaction.transaction_date, Transaction.debit)
            .all()
        )
        result = {"weekday": 0.0, "weekend": 0.0}
        for txn_date, debit in rows:
            key = "weekend" if txn_date.weekday() >= 5 else "weekday"
            result[key] += debit or 0
        return {k: round(v, 2) for k, v in result.items()}

    def large_transactions(self, account_id=None, start=None, end=None, limit: int = 10) -> List[Dict]:
        q = (
            _base_query(self.db, self.user_id, account_id, start, end)
            .filter(Transaction.transaction_type.in_(INCLUDED_EXPENSE_TYPES))
            .order_by(Transaction.debit.desc())
            .limit(limit)
        )
        return [
            {
                "id": t.id, "date": t.transaction_date.isoformat(), "description": t.normalized_description,
                "amount": t.debit, "category_id": t.category_id,
            }
            for t in q.all()
        ]

    def compare_periods(self, account_id, period_a: Tuple[date, date], period_b: Tuple[date, date]) -> Dict:
        a = self.overview(account_id, period_a[0], period_a[1])
        b = self.overview(account_id, period_b[0], period_b[1])
        pct = lambda new, old: round((new - old) / old * 100, 2) if old else 0.0  # noqa: E731
        return {
            "period_a": {"income": a.total_income, "expenses": a.total_expenses},
            "period_b": {"income": b.total_income, "expenses": b.total_expenses},
            "income_change_pct": pct(a.total_income, b.total_income),
            "expense_change_pct": pct(a.total_expenses, b.total_expenses),
        }
