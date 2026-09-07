"""Chat entry point. Advanced providers (OpenAI, Anthropic) drive their own multi-round tool
calling in AIProvider.answer_with_tools, picking whatever FinancialTools methods they need to
answer an arbitrary free-text question. Providers without native tool calling fall back to the
keyword-based single-shot routing below, which only ever hands the LLM numbers tools.py already
computed -- it never invents financial figures itself."""
import re
from dataclasses import dataclass
from datetime import date
from typing import Dict, Optional, Tuple

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from app.ai.base import AIProvider
from app.ai.tools import FinancialTools
from app.services.category_rules import DEFAULT_CATEGORIES

_CATEGORY_NAMES = [c[0] for c in DEFAULT_CATEGORIES]

_MONTH_NAMES = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}


@dataclass
class ChatAnswer:
    text: str
    structured_data: Dict
    fact_type: str  # FACT|CALCULATION|INSIGHT|RECOMMENDATION


def _resolve_period(question: str, today: date) -> Optional[tuple]:
    q = question.lower()
    if "this month" in q:
        return today.replace(day=1), today
    if "last month" in q:
        end = today.replace(day=1) - relativedelta(days=1)
        return end.replace(day=1), end
    if "this year" in q:
        return today.replace(month=1, day=1), today
    for name, num in _MONTH_NAMES.items():
        if name in q:
            year = today.year
            start = date(year, num, 1)
            end = (start + relativedelta(months=1)) - relativedelta(days=1)
            return start, end
    return None


def _extract_amount(question: str) -> Optional[float]:
    match = re.search(r"(?:₹|rs\.?|inr)\s*([\d,]+)", question, re.I)
    if match:
        return float(match.group(1).replace(",", ""))
    match = re.search(r"above\s+([\d,]+)", question, re.I)
    if match:
        return float(match.group(1).replace(",", ""))
    return None


def _extract_category(question: str) -> Optional[str]:
    for name in _CATEGORY_NAMES:
        if name.lower() in question.lower():
            return name
    return None


def route_question(db: Session, user_id: str, question: str, provider: AIProvider, today: Optional[date] = None) -> ChatAnswer:
    today = today or date.today()
    tools = FinancialTools(db, user_id)
    text, data = provider.answer_with_tools(question, tools, today)
    return ChatAnswer(text=text, structured_data=data, fact_type="FACT")


def route_question_fallback(question: str, tools: FinancialTools, provider: AIProvider, today: Optional[date] = None) -> Tuple[str, Dict]:
    """Single-shot keyword-based routing, used by providers without native tool calling."""
    today = today or date.today()
    period = _resolve_period(question, today)
    start, end = period if period else (None, None)
    q = question.lower()

    if "recurring" in q or "subscription" in q:
        data = tools.get_recurring_transactions()
    elif "account" in q or "balance" in q:
        data = tools.list_accounts()
    elif "above" in q or "large" in q or "biggest" in q:
        amount = _extract_amount(question) or 50000
        data = tools.get_large_transactions(amount, start, end)
    elif "compare" in q and "last month" in q:
        this_start = today.replace(day=1)
        last_end = this_start - relativedelta(days=1)
        last_start = last_end.replace(day=1)
        data = tools.compare_periods(this_start, today, last_start, last_end)
    elif "save" in q or "savings" in q:
        data = tools.get_savings_rate(start, end)
    elif "income" in q or "earn" in q:
        data = tools.get_total_income(start, end)
    else:
        category = _extract_category(question)
        if category:
            data = tools.get_category_spending(category, start, end)
        else:
            merchant = re.search(r"(?:at|from|on)\s+([a-zA-Z][\w& ]{1,30})", question)
            if merchant:
                data = tools.get_merchant_spending(merchant.group(1).strip(), start, end)
            else:
                data = tools.get_total_expenses(start, end)

    if not provider.is_available:
        text = _fallback_explanation(data)
    else:
        text = provider.answer_financial_question(question, data)

    return text, data


def _fallback_explanation(data: Dict) -> str:
    if not data or all(v in (None, 0, [], {}) for v in data.values()):
        return "I don't have enough transaction data to answer that."
    parts = []
    for key, value in data.items():
        if isinstance(value, (int, float)):
            parts.append(f"{key.replace('_', ' ')}: {value:,.2f}" if isinstance(value, float) else f"{key.replace('_', ' ')}: {value}")
        elif isinstance(value, list) and value:
            parts.append(f"{key.replace('_', ' ')}: {len(value)} item(s)")
    return "Based on your transaction data — " + "; ".join(parts) + "." if parts else "I don't have enough transaction data to answer that."
