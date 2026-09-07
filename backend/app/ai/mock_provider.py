"""Deterministic mock provider so the app is fully usable without any API key."""
from typing import Dict, List

from app.ai.base import AIProvider, CategorizationResult


class MockAIProvider(AIProvider):
    name = "mock"
    is_available = True

    def categorize_transaction(self, description: str, amount: float, candidate_categories: List[str]) -> CategorizationResult:
        category = candidate_categories[0] if candidate_categories else "Other"
        return CategorizationResult(
            category=category,
            subcategory=None,
            merchant=description.split(" ")[0].title() if description else "Unknown",
            confidence=0.6,
            reason="Mock provider: assigned based on the first candidate category (no live AI configured).",
        )

    def generate_insight_text(self, insight_type: str, facts: Dict) -> str:
        return facts.get("explanation", f"Insight of type {insight_type} detected.")

    def answer_financial_question(self, question: str, structured_data: Dict) -> str:
        if not structured_data or all(v in (None, 0, [], {}) for v in structured_data.values()):
            return "I don't have enough transaction data to answer that."
        parts = []
        for key, value in structured_data.items():
            label = key.replace("_", " ")
            if isinstance(value, float):
                parts.append(f"{label} is ₹{value:,.2f}" if "rate" not in key and "pct" not in key else f"{label} is {value:.2f}%")
            elif isinstance(value, int):
                parts.append(f"{label} is {value:,}")
            elif isinstance(value, list):
                parts.append(f"{label}: {len(value)} item(s)")
            else:
                parts.append(f"{label}: {value}")
        return "Based on your transaction data — " + "; ".join(parts) + "."

    def generate_summary(self, period_label: str, facts: Dict) -> str:
        income = facts.get("total_income", 0)
        expenses = facts.get("total_expenses", 0)
        return (
            f"In {period_label}, you earned ₹{income:,.0f} and spent ₹{expenses:,.0f}, "
            f"leaving a net cash flow of ₹{income - expenses:,.0f}."
        )
