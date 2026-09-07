"""Statement period overlap detection against existing statements for the same account."""
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import List, Optional


class OverlapType(str, Enum):
    EXACT_DUPLICATE = "exact_duplicate"
    PARTIAL_OVERLAP = "partial_overlap"
    FULL_CONTAINMENT = "full_containment"  # new period is fully covered by an existing one
    CONTAINS_EXISTING = "contains_existing"  # new period fully covers an existing one
    NONE = "none"


@dataclass
class ExistingPeriod:
    statement_id: str
    start: date
    end: date


@dataclass
class OverlapResult:
    overlap_type: OverlapType
    message: str
    conflicting_statement_ids: List[str]


def _ranges_overlap(a_start: date, a_end: date, b_start: date, b_end: date) -> bool:
    return a_start <= b_end and b_start <= a_end


def detect_overlap(new_start: date, new_end: date, existing_periods: List[ExistingPeriod]) -> OverlapResult:
    conflicts = [p for p in existing_periods if _ranges_overlap(new_start, new_end, p.start, p.end)]
    if not conflicts:
        return OverlapResult(OverlapType.NONE, "No overlap detected.", [])

    for p in conflicts:
        if new_start == p.start and new_end == p.end:
            return OverlapResult(
                OverlapType.EXACT_DUPLICATE, "Duplicate statement detected.", [p.statement_id]
            )

    for p in conflicts:
        if p.start <= new_start and new_end <= p.end:
            return OverlapResult(
                OverlapType.FULL_CONTAINMENT,
                "Uploaded period is already covered by an existing statement.",
                [p.statement_id],
            )

    for p in conflicts:
        if new_start <= p.start and p.end <= new_end:
            return OverlapResult(
                OverlapType.CONTAINS_EXISTING,
                "Uploaded statement fully covers an existing statement's period.",
                [p.statement_id],
            )

    return OverlapResult(
        OverlapType.PARTIAL_OVERLAP,
        "Statement period overlaps with existing data.",
        [p.statement_id for p in conflicts],
    )
