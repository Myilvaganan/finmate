"""Google Gemini provider via REST (avoids an extra SDK dependency). Never called from the frontend."""
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


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self):
        settings = get_settings()
        self.model = settings.AI_MODEL or "gemini-1.5-flash"
        self.api_key = settings.AI_API_KEY
        self.is_available = bool(self.api_key)

    def _generate(self, system: str, user: str) -> str:
        if not self.is_available:
            return ""
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            f"?key={self.api_key}"
        )
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user}]}],
        }
        try:
            resp = httpx.post(url, json=payload, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as exc:
            logger.warning("Gemini request failed: %s", type(exc).__name__)
            return ""

    def categorize_transaction(self, description: str, amount: float, candidate_categories: List[str]) -> CategorizationResult:
        prompt = (
            f"Transaction description: {description}\nAmount: {amount}\n"
            f"Pick the best category from: {candidate_categories}.\n"
            'Respond with JSON only: {"category": "...", "subcategory": "...", "merchant": "...", '
            '"confidence": 0-1, "reason": "..."}'
        )
        raw = self._generate(CATEGORIZER_SYSTEM_PROMPT, prompt)
        try:
            cleaned = raw.strip().strip("`").removeprefix("json").strip()
            data = json.loads(cleaned)
            return CategorizationResult(
                category=data.get("category", "Other"), subcategory=data.get("subcategory"),
                merchant=data.get("merchant", ""), confidence=float(data.get("confidence", 0.5)),
                reason=data.get("reason", ""),
            )
        except (json.JSONDecodeError, ValueError):
            return CategorizationResult("Other", None, "", 0.3, "Could not parse AI response.")

    def generate_insight_text(self, insight_type: str, facts: Dict) -> str:
        return self._generate(
            INSIGHT_EXPLAINER_SYSTEM_PROMPT,
            f"Insight type: {insight_type}\nFacts: {json.dumps(facts)}",
        ) or facts.get("explanation", "")

    def answer_financial_question(self, question: str, structured_data: Dict) -> str:
        return self._generate(
            FINANCIAL_ASSISTANT_SYSTEM_PROMPT,
            f"Question: {question}\nStructured data: {json.dumps(structured_data, default=str)}",
        ) or "I don't have enough transaction data to answer that."

    def generate_summary(self, period_label: str, facts: Dict) -> str:
        return self._generate(
            SUMMARY_SYSTEM_PROMPT,
            f"Period: {period_label}\nFacts: {json.dumps(facts)}",
        )
