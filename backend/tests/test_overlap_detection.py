"""Critical overlap tests -- see spec section 76. These four cases must never regress."""
from datetime import date

from app.services.overlap_detection import ExistingPeriod, OverlapType, detect_overlap


def test_exact_duplicate():
    existing = [ExistingPeriod("s1", date(2026, 1, 1), date(2026, 1, 31))]
    result = detect_overlap(date(2026, 1, 1), date(2026, 1, 31), existing)
    assert result.overlap_type == OverlapType.EXACT_DUPLICATE
    assert result.message == "Duplicate statement detected."


def test_partial_overlap():
    existing = [ExistingPeriod("s1", date(2026, 1, 1), date(2026, 1, 31))]
    result = detect_overlap(date(2026, 1, 15), date(2026, 2, 15), existing)
    assert result.overlap_type == OverlapType.PARTIAL_OVERLAP
    assert result.message == "Statement period overlaps with existing data."


def test_full_containment():
    existing = [ExistingPeriod("s1", date(2026, 1, 1), date(2026, 3, 31))]
    result = detect_overlap(date(2026, 2, 1), date(2026, 2, 28), existing)
    assert result.overlap_type == OverlapType.FULL_CONTAINMENT
    assert result.message == "Uploaded period is already covered by an existing statement."


def test_no_overlap_adjacent():
    existing = [ExistingPeriod("s1", date(2026, 1, 1), date(2026, 1, 31))]
    result = detect_overlap(date(2026, 2, 1), date(2026, 2, 28), existing)
    assert result.overlap_type == OverlapType.NONE
    assert result.message == "No overlap detected."


def test_contains_existing_reverse_case():
    existing = [ExistingPeriod("s1", date(2026, 2, 1), date(2026, 2, 28))]
    result = detect_overlap(date(2026, 1, 1), date(2026, 3, 31), existing)
    assert result.overlap_type == OverlapType.CONTAINS_EXISTING


def test_no_existing_periods():
    result = detect_overlap(date(2026, 1, 1), date(2026, 1, 31), [])
    assert result.overlap_type == OverlapType.NONE
