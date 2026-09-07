"""Exact and fuzzy transaction duplicate detection against existing transactions."""
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from typing import List, Optional

from app.services.normalization import NormalizedTransaction
from app.utils.fingerprint import fuzzy_duplicate_score


class DuplicateConfidence(str, Enum):
    EXACT = "exact_duplicate"
    LIKELY = "likely_duplicate"
    POSSIBLE = "possible_duplicate"
    NONE = "none"


@dataclass
class ExistingTxnRef:
    id: str
    fingerprint: str
    transaction_date: object
    amount: float
    normalized_description: str


@dataclass
class DuplicateMatch:
    confidence: DuplicateConfidence
    score: float
    matched_transaction_id: Optional[str]


def check_duplicate(
    candidate: NormalizedTransaction, existing: List[ExistingTxnRef]
) -> DuplicateMatch:
    for e in existing:
        if e.fingerprint == candidate.fingerprint:
            return DuplicateMatch(DuplicateConfidence.EXACT, 1.0, e.id)

    best_score, best_id = 0.0, None
    for e in existing:
        if abs((candidate.transaction_date - e.transaction_date).days) > 3:
            continue
        score = fuzzy_duplicate_score(
            candidate.transaction_date, e.transaction_date,
            candidate.amount, e.amount,
            candidate.normalized_description, e.normalized_description,
        )
        if score > best_score:
            best_score, best_id = score, e.id

    if best_score >= 0.9:
        return DuplicateMatch(DuplicateConfidence.LIKELY, best_score, best_id)
    if best_score >= 0.7:
        return DuplicateMatch(DuplicateConfidence.POSSIBLE, best_score, best_id)
    return DuplicateMatch(DuplicateConfidence.NONE, best_score, None)


def find_duplicates(
    candidates: List[NormalizedTransaction], existing: List[ExistingTxnRef]
) -> List[DuplicateMatch]:
    return [check_duplicate(c, existing) for c in candidates]
