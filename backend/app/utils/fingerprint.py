"""Deterministic transaction fingerprinting for duplicate detection."""
import hashlib
import re
from datetime import date
from difflib import SequenceMatcher


def normalize_for_hash(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().upper())


def transaction_fingerprint(
    account_id: str,
    transaction_date: date,
    normalized_description: str,
    debit: float,
    credit: float,
    reference_number: str = "",
) -> str:
    parts = [
        account_id,
        transaction_date.isoformat(),
        normalize_for_hash(normalized_description),
        f"{round(debit, 2):.2f}",
        f"{round(credit, 2):.2f}",
        normalize_for_hash(reference_number or ""),
    ]
    payload = "|".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def description_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_for_hash(a), normalize_for_hash(b)).ratio()


def fuzzy_duplicate_score(
    date_a: date, date_b: date, amount_a: float, amount_b: float, desc_a: str, desc_b: str
) -> float:
    """Returns a 0-1 confidence that two transactions are the same real-world event."""
    day_diff = abs((date_a - date_b).days)
    date_score = max(0.0, 1.0 - day_diff / 3.0) if day_diff <= 3 else 0.0
    amount_score = 1.0 if abs(amount_a - amount_b) < 0.01 else 0.0
    desc_score = description_similarity(desc_a, desc_b)
    return round(0.4 * date_score + 0.4 * amount_score + 0.2 * desc_score, 3)
