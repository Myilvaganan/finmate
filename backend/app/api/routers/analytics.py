from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics.anomalies import detect_anomalies
from app.analytics.engine import AnalyticsEngine
from app.analytics.insights import generate_smart_insights
from app.analytics.recurring import detect_recurring
from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.category import Category, Merchant
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.common import success

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _period(start: Optional[date], end: Optional[date]):
    if not end:
        end = date.today()
    if not start:
        start = end - timedelta(days=30)
    return start, end


@router.get("/overview")
def overview(
    start_date: Optional[date] = None, end_date: Optional[date] = None, account_id: Optional[str] = None,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    start, end = _period(start_date, end_date)
    engine = AnalyticsEngine(db, user.id)
    metrics = engine.overview(account_id, start, end)
    return success(metrics.__dict__, meta={"period_start": start.isoformat(), "period_end": end.isoformat()})


@router.get("/income")
def income(start_date: Optional[date] = None, end_date: Optional[date] = None, account_id: Optional[str] = None,
           user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    start, end = _period(start_date, end_date)
    engine = AnalyticsEngine(db, user.id)
    return success({"total_income": engine.total_income(account_id, start, end), "monthly": engine.monthly_series(account_id, start, end)})


@router.get("/expenses")
def expenses(start_date: Optional[date] = None, end_date: Optional[date] = None, account_id: Optional[str] = None,
             user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    start, end = _period(start_date, end_date)
    engine = AnalyticsEngine(db, user.id)
    return success({
        "total_expenses": engine.total_expenses(account_id, start, end),
        "by_category": engine.category_breakdown(account_id, start, end),
        "daily": engine.daily_spending(account_id, start, end),
        "essential_vs_discretionary": engine.essential_vs_discretionary(account_id, start, end),
    })


@router.get("/categories")
def categories(start_date: Optional[date] = None, end_date: Optional[date] = None, account_id: Optional[str] = None,
               compare_previous: bool = True, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    start, end = _period(start_date, end_date)
    engine = AnalyticsEngine(db, user.id)
    return success(engine.category_breakdown(account_id, start, end, compare_previous=compare_previous))


@router.get("/merchants")
def merchants(start_date: Optional[date] = None, end_date: Optional[date] = None, account_id: Optional[str] = None,
              limit: int = 10, compare_previous: bool = True,
              user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    start, end = _period(start_date, end_date)
    engine = AnalyticsEngine(db, user.id)
    return success(engine.merchant_ranking(account_id, start, end, limit, compare_previous=compare_previous))


@router.get("/cashflow")
def cashflow(start_date: Optional[date] = None, end_date: Optional[date] = None, account_id: Optional[str] = None,
             user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    start, end = _period(start_date, end_date)
    engine = AnalyticsEngine(db, user.id)
    return success({
        "monthly": engine.cashflow_series(account_id, start, end),
        "payment_methods": engine.payment_method_breakdown(account_id, start, end),
        "accounts": engine.account_balances(),
    })


@router.get("/savings-rate")
def savings_rate(start_date: Optional[date] = None, end_date: Optional[date] = None, account_id: Optional[str] = None,
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    start, end = _period(start_date, end_date)
    engine = AnalyticsEngine(db, user.id)
    return success({
        "current": engine.savings_rate(account_id, start, end),
        "monthly": engine.savings_rate_series(account_id, start, end),
    })


@router.get("/categories/trend")
def category_trend(
    category_ids: str, start_date: Optional[date] = None, end_date: Optional[date] = None,
    account_id: Optional[str] = None, user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    """category_ids is a comma-separated list, e.g. ?category_ids=id1,id2,id3 (max 5)."""
    ids = [c for c in category_ids.split(",") if c][:5]
    start, end = _period(start_date, end_date)
    engine = AnalyticsEngine(db, user.id)
    return success(engine.category_trend(ids, account_id, start, end))


@router.get("/expenses/fixed-variable")
def fixed_variable(start_date: Optional[date] = None, end_date: Optional[date] = None, account_id: Optional[str] = None,
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    start, end = _period(start_date, end_date)
    engine = AnalyticsEngine(db, user.id)
    return success(engine.fixed_vs_variable(account_id, start, end))


@router.get("/accounts/balance-trend")
def account_balance_trend(start_date: Optional[date] = None, end_date: Optional[date] = None,
                           account_id: Optional[str] = None,
                           user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    start, end = _period(start_date, end_date)
    engine = AnalyticsEngine(db, user.id)
    return success(engine.account_balance_trend(account_id, start, end))


@router.get("/expenses/heatmap")
def spending_heatmap(year: int, account_id: Optional[str] = None,
                      user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    engine = AnalyticsEngine(db, user.id)
    return success(engine.spending_heatmap(year, account_id))


@router.get("/anomalies")
def anomalies(account_id: Optional[str] = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    engine = AnalyticsEngine(db, user.id)
    found = detect_anomalies(engine, account_id, date.today())
    return success([a.__dict__ for a in found])


def _detect_recurring_for_user(db: Session, user_id: str):
    txns = db.query(Transaction).filter(Transaction.user_id == user_id, Transaction.is_excluded == False).all()  # noqa: E712
    merchant_names = {m.id: m.display_name for m in db.query(Merchant).all()}
    categories = db.query(Category).all()
    category_names = {c.id: c.name for c in categories}
    category_parent_types = {c.id: c.parent_type for c in categories}
    category_groups = {c.id: c.group_name for c in categories}
    return detect_recurring(txns, merchant_names, category_names, category_parent_types, category_groups)


@router.get("/recurring")
def recurring(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    candidates = _detect_recurring_for_user(db, user.id)
    return success([
        {
            "merchant": c.merchant_name, "average_amount": c.average_amount, "frequency": c.frequency,
            "occurrences": c.occurrences, "last_charged_date": c.last_charged_date.isoformat(),
            "next_expected_date": c.next_expected_date.isoformat(), "annualized_cost": c.annualized_cost,
            "is_subscription": c.is_subscription, "category": c.category_name, "is_loan": c.is_loan,
        }
        for c in candidates
    ])


@router.get("/emi")
def existing_emis(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    candidates = [c for c in _detect_recurring_for_user(db, user.id) if c.is_loan]
    total_monthly = sum(
        c.average_amount if c.frequency == "monthly" else c.annualized_cost / 12 for c in candidates
    )
    return success({
        "emis": [
            {
                "merchant": c.merchant_name, "average_amount": c.average_amount, "frequency": c.frequency,
                "occurrences": c.occurrences, "last_charged_date": c.last_charged_date.isoformat(),
                "next_expected_date": c.next_expected_date.isoformat(), "annualized_cost": c.annualized_cost,
            }
            for c in candidates
        ],
        "total_monthly_emi": round(total_monthly, 2),
        "count": len(candidates),
    })


@router.get("/weekday-vs-weekend")
def weekday_vs_weekend(start_date: Optional[date] = None, end_date: Optional[date] = None, account_id: Optional[str] = None,
                        user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    start, end = _period(start_date, end_date)
    engine = AnalyticsEngine(db, user.id)
    return success(engine.weekday_vs_weekend(account_id, start, end))


@router.get("/large-transactions")
def large_transactions(start_date: Optional[date] = None, end_date: Optional[date] = None, account_id: Optional[str] = None,
                        limit: int = 10, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    start, end = _period(start_date, end_date)
    engine = AnalyticsEngine(db, user.id)
    return success(engine.large_transactions(account_id, start, end, limit))


@router.get("/insights")
def insights(account_id: Optional[str] = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    engine = AnalyticsEngine(db, user.id)
    generated = generate_smart_insights(engine, account_id, date.today())
    return success([i.__dict__ for i in generated])
