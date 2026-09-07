"""Deterministic rule-based categorization. AI is used only when rules can't decide (see ai/chat_service usage in statement_import)."""
from typing import Dict, Optional, Tuple

from app.services.category_rules import KEYWORD_RULES


def rule_based_category(
    normalized_description: str,
    merchant_name: str,
    is_credit: bool,
    learned_rules: Optional[Dict[str, str]] = None,
) -> Tuple[Optional[str], float, str]:
    """Returns (category_name, confidence, source). category_name is None if no rule matched."""
    haystack = f"{normalized_description} {merchant_name}".upper()

    if learned_rules:
        for pattern, category in learned_rules.items():
            if pattern.upper() in haystack:
                return category, 0.95, "user"

    for category, keywords in KEYWORD_RULES.items():
        if any(kw in haystack for kw in keywords):
            return category, 0.85, "rule"

    if is_credit:
        return "Other Income", 0.3, "default"
    return None, 0.0, "none"
