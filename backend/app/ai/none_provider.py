"""No-op provider used when AI_PROVIDER=none. All AI-specific features degrade gracefully."""
from typing import Dict, List

from app.ai.base import AIProvider, CategorizationResult


class NoAIProvider(AIProvider):
    name = "none"
    is_available = False

    def categorize_transaction(self, description: str, amount: float, candidate_categories: List[str]) -> CategorizationResult:
        return CategorizationResult(
            category="Other", subcategory=None, merchant="", confidence=0.0,
            reason="AI is not configured; left for manual categorization.",
        )

    def generate_insight_text(self, insight_type: str, facts: Dict) -> str:
        return facts.get("explanation", "")

    def answer_financial_question(self, question: str, structured_data: Dict) -> str:
        return "AI Assistant is not configured. Enable an AI provider in Settings to ask questions in natural language."

    def generate_summary(self, period_label: str, facts: Dict) -> str:
        return ""
