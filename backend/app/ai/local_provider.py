"""Local LLM provider: talks to any OpenAI-compatible local server (Ollama, LM Studio, vLLM)
via AI_BASE_URL. No API key required."""
import json
from typing import Dict, List

import httpx

from app.ai.base import AIProvider, CategorizationResult
from app.ai.prompts import (
    CATEGORIZER_SYSTEM_PROMPT, FINANCIAL_ASSISTANT_SYSTEM_PROMPT,
    INSIGHT_EXPLAINER_SYSTEM_PROMPT, SUMMARY_SYSTEM_PROMPT,
)
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class LocalLLMProvider(AIProvider):
    name = "local"

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.AI_BASE_URL or "http://localhost:11434/v1"
        self.model = settings.AI_MODEL or "llama3"
        self.is_available = bool(self.base_url)

    def _chat(self, system: str, user: str) -> str:
        try:
            resp = httpx.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                    "temperature": 0.2,
                },
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.warning("Local LLM request failed: %s", type(exc).__name__)
            return ""

    def categorize_transaction(self, description: str, amount: float, candidate_categories: List[str]) -> CategorizationResult:
        prompt = (
            f"Transaction description: {description}\nAmount: {amount}\n"
            f"Pick the best category from: {candidate_categories}.\n"
            'Respond with JSON only: {"category": "...", "subcategory": "...", "merchant": "...", '
            '"confidence": 0-1, "reason": "..."}'
        )
        raw = self._chat(CATEGORIZER_SYSTEM_PROMPT, prompt)
        try:
            data = json.loads(raw)
            return CategorizationResult(
                category=data.get("category", "Other"), subcategory=data.get("subcategory"),
                merchant=data.get("merchant", ""), confidence=float(data.get("confidence", 0.5)),
                reason=data.get("reason", ""),
            )
        except (json.JSONDecodeError, ValueError):
            return CategorizationResult("Other", None, "", 0.3, "Could not parse AI response.")

    def generate_insight_text(self, insight_type: str, facts: Dict) -> str:
        return self._chat(
            INSIGHT_EXPLAINER_SYSTEM_PROMPT,
            f"Insight type: {insight_type}\nFacts: {json.dumps(facts)}",
        ) or facts.get("explanation", "")

    def answer_financial_question(self, question: str, structured_data: Dict) -> str:
        return self._chat(
            FINANCIAL_ASSISTANT_SYSTEM_PROMPT,
            f"Question: {question}\nStructured data: {json.dumps(structured_data, default=str)}",
        ) or "I don't have enough transaction data to answer that."

    def generate_summary(self, period_label: str, facts: Dict) -> str:
        return self._chat(
            SUMMARY_SYSTEM_PROMPT,
            f"Period: {period_label}\nFacts: {json.dumps(facts)}",
        )
