"""AI provider abstraction. The application must work fully without any provider configured
(AI_PROVIDER=none) -- all financial computation lives outside this module."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional


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
