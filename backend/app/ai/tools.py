"""Structured tool functions the chat pipeline invokes to fetch real numbers from the database.
The LLM never computes financial figures itself -- it only explains what these return.

TOOL_SCHEMAS describes every callable in OpenAI/Anthropic function-calling format so an
advanced provider can pick whichever tools (and however many rounds of them) it needs to
answer an arbitrary free-text question grounded in the user's real statements."""
from datetime import date, datetime
from typing import Dict, List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.analytics.engine import AnalyticsEngine
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.category import Category, Merchant


def _to_date(value) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


class FinancialTools:
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id
        self.engine = AnalyticsEngine(db, user_id)

    # -- single-number facts -------------------------------------------------
    def get_total_income(self, start: Optional[date] = None, end: Optional[date] = None) -> Dict:
        return {"total_income": self.engine.total_income(start=start, end=end)}

    def get_total_expenses(self, start: Optional[date] = None, end: Optional[date] = None) -> Dict:
        return {"total_expenses": self.engine.total_expenses(start=start, end=end)}

    def get_cash_flow(self, start: Optional[date] = None, end: Optional[date] = None) -> Dict:
        return {"net_cash_flow": self.engine.net_cash_flow(start=start, end=end)}

    def get_savings_rate(self, start: Optional[date] = None, end: Optional[date] = None) -> Dict:
        return {"savings_rate_pct": self.engine.savings_rate(start=start, end=end)}

    def get_overview(self, start: Optional[date] = None, end: Optional[date] = None) -> Dict:
        return self.engine.overview(start=start, end=end).__dict__

    # -- breakdowns ------------------------------------------------------------
    def get_category_breakdown(self, start: Optional[date] = None, end: Optional[date] = None) -> Dict:
        return {"categories": self.engine.category_breakdown(start=start, end=end)}

    def get_merchant_ranking(self, start: Optional[date] = None, end: Optional[date] = None, limit: int = 15) -> Dict:
        return {"merchants": self.engine.merchant_ranking(start=start, end=end, limit=limit)}

    def get_monthly_trend(self, start: Optional[date] = None, end: Optional[date] = None) -> Dict:
        return {"monthly": self.engine.monthly_series(start=start, end=end)}

    def get_essential_vs_discretionary(self, start: Optional[date] = None, end: Optional[date] = None) -> Dict:
        return self.engine.essential_vs_discretionary(start=start, end=end)

    def get_payment_method_breakdown(self, start: Optional[date] = None, end: Optional[date] = None) -> Dict:
        return {"payment_methods": self.engine.payment_method_breakdown(start=start, end=end)}

    def get_weekday_vs_weekend(self, start: Optional[date] = None, end: Optional[date] = None) -> Dict:
        return self.engine.weekday_vs_weekend(start=start, end=end)

    # -- targeted lookups --------------------------------------------------
    def get_category_spending(self, category_name: str, start: Optional[date] = None, end: Optional[date] = None) -> Dict:
        q = (
            self.db.query(func.sum(Transaction.debit), func.count(Transaction.id))
            .join(Category, Transaction.category_id == Category.id)
            .filter(
                Transaction.user_id == self.user_id, Transaction.is_excluded == False,  # noqa: E712
                Transaction.transaction_type == "expense", func.lower(Category.name) == category_name.lower(),
            )
        )
        if start:
            q = q.filter(Transaction.transaction_date >= start)
        if end:
            q = q.filter(Transaction.transaction_date <= end)
        total, count = q.one()
        return {"category": category_name, "total": round(total or 0, 2), "transaction_count": count}

    def get_merchant_spending(self, merchant_name: str, start: Optional[date] = None, end: Optional[date] = None) -> Dict:
        q = (
            self.db.query(func.sum(Transaction.debit), func.count(Transaction.id))
            .join(Merchant, Transaction.merchant_id == Merchant.id)
            .filter(
                Transaction.user_id == self.user_id, Transaction.is_excluded == False,  # noqa: E712
                func.lower(Merchant.normalized_name).like(f"%{merchant_name.lower()}%"),
            )
        )
        if start:
            q = q.filter(Transaction.transaction_date >= start)
        if end:
            q = q.filter(Transaction.transaction_date <= end)
        total, count = q.one()
        return {"merchant": merchant_name, "total": round(total or 0, 2), "transaction_count": count}

    def get_large_transactions(self, min_amount: float, start: Optional[date] = None, end: Optional[date] = None, limit: int = 20) -> Dict:
        q = self.db.query(Transaction).filter(
            Transaction.user_id == self.user_id, Transaction.is_excluded == False,  # noqa: E712
            Transaction.debit >= min_amount,
        )
        if start:
            q = q.filter(Transaction.transaction_date >= start)
        if end:
            q = q.filter(Transaction.transaction_date <= end)
        rows = q.order_by(Transaction.debit.desc()).limit(limit).all()
        return {
            "transactions": [
                {"date": t.transaction_date.isoformat(), "description": t.normalized_description, "amount": t.debit}
                for t in rows
            ]
        }

    def get_recurring_transactions(self) -> Dict:
        from app.models.recurring import RecurringTransaction
        rows = self.db.query(RecurringTransaction).filter(
            RecurringTransaction.user_id == self.user_id, RecurringTransaction.is_dismissed == False,  # noqa: E712
        ).all()
        return {
            "recurring": [
                {"merchant": r.merchant_name, "amount": r.average_amount, "frequency": r.frequency}
                for r in rows
            ]
        }

    def get_existing_emis(self) -> Dict:
        from app.analytics.recurring import detect_recurring

        txns = self.db.query(Transaction).filter(
            Transaction.user_id == self.user_id, Transaction.is_excluded == False,  # noqa: E712
        ).all()
        merchant_names = {m.id: m.display_name for m in self.db.query(Merchant).all()}
        category_names = {c.id: c.name for c in self.db.query(Category).all()}
        candidates = [c for c in detect_recurring(txns, merchant_names, category_names) if c.is_loan]
        total_monthly = sum(
            c.average_amount if c.frequency == "monthly" else c.annualized_cost / 12 for c in candidates
        )
        return {
            "emis": [
                {
                    "merchant": c.merchant_name, "amount": c.average_amount, "frequency": c.frequency,
                    "next_due_date": c.next_expected_date.isoformat(), "annualized_cost": c.annualized_cost,
                }
                for c in candidates
            ],
            "total_monthly_emi": round(total_monthly, 2),
        }

    def compare_periods(
        self, period_a_start: date, period_a_end: date, period_b_start: date, period_b_end: date,
    ) -> Dict:
        return self.engine.compare_periods(None, (period_a_start, period_a_end), (period_b_start, period_b_end))

    def get_account_balance(self) -> Dict:
        return {"accounts": self.engine.account_balances()}

    def list_accounts(self) -> Dict:
        accounts = self.db.query(Account).filter(Account.user_id == self.user_id).all()
        return {
            "accounts": [
                {
                    "account_id": a.id, "bank_name": a.bank_name, "account_type": a.account_type,
                    "masked_account_number": a.masked_account_number, "opening_balance": a.opening_balance,
                    "closing_balance": a.closing_balance, "currency": a.currency,
                }
                for a in accounts
            ]
        }

    def get_data_overview(self) -> Dict:
        """What data actually exists: date range, transaction count, banks -- lets the model
        know the scope of statements available before answering, or explain gaps honestly."""
        base = self.db.query(Transaction).filter(Transaction.user_id == self.user_id)
        earliest = base.order_by(Transaction.transaction_date.asc()).first()
        latest = base.order_by(Transaction.transaction_date.desc()).first()
        banks = [row[0] for row in self.db.query(Account.bank_name).filter(Account.user_id == self.user_id).distinct().all()]
        return {
            "earliest_transaction_date": earliest.transaction_date.isoformat() if earliest else None,
            "latest_transaction_date": latest.transaction_date.isoformat() if latest else None,
            "total_transactions": base.count(),
            "banks": banks,
        }

    def search_transactions(
        self, keyword: Optional[str] = None, category: Optional[str] = None, merchant: Optional[str] = None,
        bank: Optional[str] = None, transaction_type: Optional[str] = None, payment_method: Optional[str] = None,
        min_amount: Optional[float] = None, max_amount: Optional[float] = None,
        start: Optional[date] = None, end: Optional[date] = None, limit: int = 30,
    ) -> Dict:
        """Free-form transaction search across description, merchant, category, bank, amount
        and date -- the general-purpose fallback for any question that doesn't fit a narrower
        tool (e.g. 'show me all ATM withdrawals in April' or 'transactions from my HDFC card')."""
        q = (
            self.db.query(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .outerjoin(Merchant, Transaction.merchant_id == Merchant.id)
            .outerjoin(Category, Transaction.category_id == Category.id)
            .filter(Transaction.user_id == self.user_id, Transaction.is_excluded == False)  # noqa: E712
        )
        if keyword:
            like = f"%{keyword.lower()}%"
            q = q.filter(or_(
                func.lower(Transaction.normalized_description).like(like),
                func.lower(Transaction.original_description).like(like),
            ))
        if category:
            q = q.filter(func.lower(Category.name).like(f"%{category.lower()}%"))
        if merchant:
            q = q.filter(func.lower(Merchant.normalized_name).like(f"%{merchant.lower()}%"))
        if bank:
            q = q.filter(func.lower(Account.bank_name).like(f"%{bank.lower()}%"))
        if transaction_type:
            q = q.filter(Transaction.transaction_type == transaction_type)
        if payment_method:
            q = q.filter(Transaction.payment_method == payment_method)
        if min_amount is not None:
            q = q.filter((Transaction.debit >= min_amount) | (Transaction.credit >= min_amount))
        if max_amount is not None:
            q = q.filter((Transaction.debit <= max_amount) | (Transaction.credit <= max_amount))
        if start:
            q = q.filter(Transaction.transaction_date >= start)
        if end:
            q = q.filter(Transaction.transaction_date <= end)
        total_count = q.count()
        rows = (
            q.with_entities(Transaction, Account.bank_name, Category.name)
            .order_by(Transaction.transaction_date.desc())
            .limit(min(limit, 100))
            .all()
        )
        return {
            "matching_count": total_count,
            "transactions": [
                {
                    "date": t.transaction_date.isoformat(), "description": t.normalized_description or t.original_description,
                    "debit": t.debit, "credit": t.credit, "type": t.transaction_type,
                    "payment_method": t.payment_method, "bank": bank_name, "category": category_name,
                }
                for t, bank_name, category_name in rows
            ],
        }

    # -- dispatch ------------------------------------------------------------
    _DATE_PARAMS = {"start", "end", "period_a_start", "period_a_end", "period_b_start", "period_b_end"}

    def dispatch(self, name: str, arguments: Dict) -> Dict:
        if name not in _TOOL_NAMES:
            return {"error": f"Unknown tool '{name}'."}
        method = getattr(self, name)
        kwargs = {}
        for key, value in (arguments or {}).items():
            kwargs[key] = _to_date(value) if key in self._DATE_PARAMS and value else value
        try:
            return method(**kwargs)
        except TypeError as exc:
            return {"error": f"Invalid arguments for '{name}': {exc}"}
        except Exception as exc:  # noqa: BLE001
            return {"error": f"Tool '{name}' failed: {type(exc).__name__}"}


def _prop(type_="string", description="", **extra) -> Dict:
    return {"type": type_, "description": description, **extra}


_DATE_RANGE_PROPS = {
    "start": _prop(description="Start date, ISO format YYYY-MM-DD. Omit for no lower bound."),
    "end": _prop(description="End date, ISO format YYYY-MM-DD. Omit for no upper bound."),
}

TOOL_SCHEMAS: List[Dict] = [
    {"name": "get_data_overview", "description": "Get the date range, total transaction count, and list of banks actually present in the user's imported statements. Call this first if unsure what data exists.", "parameters": {"type": "object", "properties": {}}},
    {"name": "list_accounts", "description": "List all bank accounts/cards with balances, type, and masked account number.", "parameters": {"type": "object", "properties": {}}},
    {"name": "get_account_balance", "description": "Get current balance per account.", "parameters": {"type": "object", "properties": {}}},
    {"name": "get_overview", "description": "Get overview metrics for a period: income, expenses, net cash flow, savings rate, transaction count, average/median/largest/smallest transaction.", "parameters": {"type": "object", "properties": _DATE_RANGE_PROPS}},
    {"name": "get_total_income", "description": "Total income for a period.", "parameters": {"type": "object", "properties": _DATE_RANGE_PROPS}},
    {"name": "get_total_expenses", "description": "Total expenses for a period.", "parameters": {"type": "object", "properties": _DATE_RANGE_PROPS}},
    {"name": "get_cash_flow", "description": "Net cash flow (income minus expenses) for a period.", "parameters": {"type": "object", "properties": _DATE_RANGE_PROPS}},
    {"name": "get_savings_rate", "description": "Savings rate percentage for a period.", "parameters": {"type": "object", "properties": _DATE_RANGE_PROPS}},
    {"name": "get_category_breakdown", "description": "Spending grouped by category for a period.", "parameters": {"type": "object", "properties": _DATE_RANGE_PROPS}},
    {"name": "get_merchant_ranking", "description": "Top merchants by spend for a period.", "parameters": {"type": "object", "properties": {**_DATE_RANGE_PROPS, "limit": _prop("integer", "Max merchants to return, default 15")}}},
    {"name": "get_monthly_trend", "description": "Monthly income/expense series for a period, useful for trend or comparison-over-time questions.", "parameters": {"type": "object", "properties": _DATE_RANGE_PROPS}},
    {"name": "get_essential_vs_discretionary", "description": "Split of expenses into essential vs discretionary categories for a period.", "parameters": {"type": "object", "properties": _DATE_RANGE_PROPS}},
    {"name": "get_payment_method_breakdown", "description": "Spending grouped by payment method (upi, card, netbanking, cash, etc.) for a period.", "parameters": {"type": "object", "properties": _DATE_RANGE_PROPS}},
    {"name": "get_weekday_vs_weekend", "description": "Spending split between weekdays and weekends for a period.", "parameters": {"type": "object", "properties": _DATE_RANGE_PROPS}},
    {"name": "get_category_spending", "description": "Total spent and transaction count in one specific named category.", "parameters": {"type": "object", "properties": {"category_name": _prop(description="Exact or close category name, e.g. 'Food & Dining'"), **_DATE_RANGE_PROPS}, "required": ["category_name"]}},
    {"name": "get_merchant_spending", "description": "Total spent and transaction count at one specific merchant (partial name match), e.g. 'swiggy', 'amazon'.", "parameters": {"type": "object", "properties": {"merchant_name": _prop(), **_DATE_RANGE_PROPS}, "required": ["merchant_name"]}},
    {"name": "get_large_transactions", "description": "Transactions at or above a given amount.", "parameters": {"type": "object", "properties": {"min_amount": _prop("number"), **_DATE_RANGE_PROPS, "limit": _prop("integer")}, "required": ["min_amount"]}},
    {"name": "get_recurring_transactions", "description": "Detected recurring payments and subscriptions.", "parameters": {"type": "object", "properties": {}}},
    {"name": "get_existing_emis", "description": "Detected existing EMIs / loan repayments (from the 'EMI / Loans' category), with amount, frequency, next due date, and total monthly EMI outflow.", "parameters": {"type": "object", "properties": {}}},
    {"name": "compare_periods", "description": "Compare income/expenses between two date ranges, e.g. this month vs last month.", "parameters": {"type": "object", "properties": {"period_a_start": _prop(), "period_a_end": _prop(), "period_b_start": _prop(), "period_b_end": _prop()}, "required": ["period_a_start", "period_a_end", "period_b_start", "period_b_end"]}},
    {
        "name": "search_transactions",
        "description": (
            "General-purpose transaction search across description, merchant, category, bank, "
            "payment method, amount range and date range. Use this for any question that doesn't "
            "fit a narrower tool above -- e.g. 'ATM withdrawals in April', 'transactions on my "
            "HDFC card over 1000', 'refunds from Amazon', 'cheque payments last year'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": _prop(description="Free text to match against the transaction description"),
                "category": _prop(),
                "merchant": _prop(),
                "bank": _prop(description="Bank name, e.g. 'ICICI', 'Axis'"),
                "transaction_type": _prop(description="One of: income, expense, transfer, investment, cash_withdrawal, card_payment"),
                "payment_method": _prop(description="One of: upi, card, netbanking, cash, cheque, neft_rtgs, other"),
                "min_amount": _prop("number"),
                "max_amount": _prop("number"),
                **_DATE_RANGE_PROPS,
                "limit": _prop("integer", "Max results, default 30, hard cap 100"),
            },
        },
    },
]

_TOOL_NAMES = {spec["name"] for spec in TOOL_SCHEMAS}
