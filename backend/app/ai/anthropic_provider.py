"""Anthropic provider. Never called from the frontend -- API key lives only in backend env."""
import json
from datetime import date
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from app.ai.base import AIProvider, CategorizationResult
from app.ai.prompts import (
    CATEGORIZER_SYSTEM_PROMPT, FINANCIAL_ASSISTANT_SYSTEM_PROMPT,
    INSIGHT_EXPLAINER_SYSTEM_PROMPT, SUMMARY_SYSTEM_PROMPT, TOOL_CALLING_SYSTEM_PROMPT,
)
from app.core.config import get_settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.ai.tools import FinancialTools

logger = get_logger(__name__)

_MAX_TOOL_ROUNDS = 6


class AnthropicProvider(AIProvider):
    name = "anthropic"
    supports_tool_calling = True

    def __init__(self):
        settings = get_settings()
        self.model = settings.AI_MODEL or "claude-haiku-4-5-20251001"
        self.is_available = bool(settings.AI_API_KEY)
        self._client = None
        if self.is_available:
            import anthropic
            self._client = anthropic.Anthropic(api_key=settings.AI_API_KEY)

    def _complete(self, system: str, user: str) -> str:
        if not self._client:
            return ""
        try:
            resp = self._client.messages.create(
                model=self.model, max_tokens=500, system=system,
                messages=[{"role": "user", "content": user}],
            )
            return "".join(block.text for block in resp.content if block.type == "text")
        except Exception as exc:
            logger.warning("Anthropic request failed: %s", type(exc).__name__)
            return ""

    def categorize_transaction(self, description: str, amount: float, candidate_categories: List[str]) -> CategorizationResult:
        prompt = (
            f"Transaction description: {description}\nAmount: {amount}\n"
            f"Pick the best category from: {candidate_categories}.\n"
            'Respond with JSON only: {"category": "...", "subcategory": "...", "merchant": "<clean human-readable name, or empty string if none found>", '
            '"confidence": 0-1, "reason": "..."}'
        )
        raw = self._complete(CATEGORIZER_SYSTEM_PROMPT, prompt)
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
        return self._complete(
            INSIGHT_EXPLAINER_SYSTEM_PROMPT,
            f"Insight type: {insight_type}\nFacts: {json.dumps(facts)}",
        ) or facts.get("explanation", "")

    def answer_financial_question(self, question: str, structured_data: Dict) -> str:
        return self._complete(
            FINANCIAL_ASSISTANT_SYSTEM_PROMPT,
            f"Question: {question}\nStructured data: {json.dumps(structured_data, default=str)}",
        ) or "I don't have enough transaction data to answer that."

    def generate_summary(self, period_label: str, facts: Dict) -> str:
        return self._complete(
            SUMMARY_SYSTEM_PROMPT,
            f"Period: {period_label}\nFacts: {json.dumps(facts)}",
        )

    def answer_with_tools(self, question: str, tools: "FinancialTools", today: Optional[date] = None) -> Tuple[str, Dict]:
        if not self._client:
            return super().answer_with_tools(question, tools, today)
        from app.ai.tools import TOOL_SCHEMAS

        today = today or date.today()
        schemas = [
            {"name": spec["name"], "description": spec["description"], "input_schema": spec["parameters"]}
            for spec in TOOL_SCHEMAS
        ]
        system = TOOL_CALLING_SYSTEM_PROMPT.format(today=today.isoformat())
        messages: List[Dict] = [{"role": "user", "content": question}]
        collected: Dict = {}
        try:
            for _ in range(_MAX_TOOL_ROUNDS):
                resp = self._client.messages.create(
                    model=self.model, max_tokens=800, system=system, messages=messages, tools=schemas,
                )
                messages.append({"role": "assistant", "content": resp.content})
                if resp.stop_reason != "tool_use":
                    text = "".join(block.text for block in resp.content if block.type == "text")
                    return text or "I don't have enough transaction data to answer that.", collected

                tool_results = []
                for block in resp.content:
                    if block.type != "tool_use":
                        continue
                    result = tools.dispatch(block.name, block.input or {})
                    collected[block.name] = result
                    tool_results.append({
                        "type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result, default=str),
                    })
                messages.append({"role": "user", "content": tool_results})

            final = self._client.messages.create(model=self.model, max_tokens=800, system=system, messages=messages)
            text = "".join(block.text for block in final.content if block.type == "text")
            return text or "I don't have enough transaction data to answer that.", collected
        except Exception as exc:
            logger.warning("Anthropic tool-calling chat failed: %s", type(exc).__name__)
            return super().answer_with_tools(question, tools, today)
