"""AI provider abstraction. The application must work fully without any provider configured
(AI_PROVIDER=none) -- all financial computation lives outside this module."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from app.ai.tools import FinancialTools


@dataclass
class CategorizationResult:
    category: str
    subcategory: Optional[str]
    merchant: str
    confidence: float
    reason: str


class AIProvider(ABC):
    name: str = "base"
    is_available: bool = True
    # True for providers that implement real multi-round function calling in answer_with_tools
    # (currently OpenAI and Anthropic). Others fall back to single-shot keyword routing.
    supports_tool_calling: bool = False

    @abstractmethod
    def categorize_transaction(self, description: str, amount: float, candidate_categories: List[str]) -> CategorizationResult:
        ...

    @abstractmethod
    def generate_insight_text(self, insight_type: str, facts: Dict) -> str:
        ...

    @abstractmethod
    def answer_financial_question(self, question: str, structured_data: Dict) -> str:
        ...

    @abstractmethod
    def generate_summary(self, period_label: str, facts: Dict) -> str:
        ...

    def answer_with_tools(self, question: str, tools: "FinancialTools", today: Optional[date] = None) -> Tuple[str, Dict]:
        """Answer an arbitrary free-text question grounded in the user's real data.

        Providers with native function-calling (OpenAI, Anthropic) override this to let the
        model choose which FinancialTools methods to call, over multiple rounds, based on the
        question. Providers without it fall back to single-shot keyword routing here."""
        from app.ai.chat_service import route_question_fallback
        return route_question_fallback(question, tools, self, today)
