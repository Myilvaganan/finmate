"""OpenAI provider. Never called from the frontend -- API key lives only in backend env."""
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


class OpenAIProvider(AIProvider):
    name = "openai"
    supports_tool_calling = True

    def __init__(self):
        settings = get_settings()
        self.model = settings.AI_MODEL or "gpt-4o-mini"
        self.is_available = bool(settings.AI_API_KEY)
        self._client = None
        if self.is_available:
            from openai import OpenAI
            self._client = OpenAI(api_key=settings.AI_API_KEY)

    def _chat(self, system: str, user: str) -> str:
        if not self._client:
            return ""
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.2,
            )
            return resp.choices[0].message.content or ""
        except Exception as exc:
            logger.warning("OpenAI request failed: %s", type(exc).__name__)
            return ""

    def categorize_transaction(self, description: str, amount: float, candidate_categories: List[str]) -> CategorizationResult:
        prompt = (
            f"Transaction description: {description}\nAmount: {amount}\n"
            f"Pick the best category from: {candidate_categories}.\n"
            'Respond as JSON: {"category": "...", "subcategory": "...", '
            '"merchant": "<clean human-readable name, or empty string if none found>", '
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

    def answer_with_tools(self, question: str, tools: "FinancialTools", today: Optional[date] = None) -> Tuple[str, Dict]:
        if not self._client:
            return super().answer_with_tools(question, tools, today)
        from app.ai.tools import TOOL_SCHEMAS

        today = today or date.today()
        schemas = [{"type": "function", "function": spec} for spec in TOOL_SCHEMAS]
        messages = [
            {"role": "system", "content": TOOL_CALLING_SYSTEM_PROMPT.format(today=today.isoformat())},
            {"role": "user", "content": question},
        ]
        collected: Dict = {}
        try:
            for _ in range(_MAX_TOOL_ROUNDS):
                resp = self._client.chat.completions.create(
                    model=self.model, messages=messages, tools=schemas, tool_choice="auto", temperature=0.2,
                )
                msg = resp.choices[0].message
                if not msg.tool_calls:
                    return msg.content or "I don't have enough transaction data to answer that.", collected
                messages.append({
                    "role": "assistant", "content": msg.content,
                    "tool_calls": [
                        {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                        for tc in msg.tool_calls
                    ],
                })
                for tc in msg.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    result = tools.dispatch(tc.function.name, args)
                    collected[tc.function.name] = result
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result, default=str)})

            final = self._client.chat.completions.create(model=self.model, messages=messages, temperature=0.2)
            return final.choices[0].message.content or "I don't have enough transaction data to answer that.", collected
        except Exception as exc:
            logger.warning("OpenAI tool-calling chat failed: %s", type(exc).__name__)
            return super().answer_with_tools(question, tools, today)
