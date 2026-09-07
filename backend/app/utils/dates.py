"""Date parsing utilities that prioritize Indian (DD/MM/YYYY) conventions when ambiguous."""
from datetime import date, datetime
from typing import Optional

from dateutil import parser as dateutil_parser

_KNOWN_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y",
    "%d %b %Y", "%d-%b-%Y", "%d %B %Y", "%m/%d/%Y", "%b %d, %Y",
]


def parse_transaction_date(raw: str) -> Optional[date]:
    """Attempts strict known formats first (DD/MM prioritized), falls back to dateutil with dayfirst=True."""
    if not raw:
        return None
    raw = raw.strip()
    for fmt in _KNOWN_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    try:
        return dateutil_parser.parse(raw, dayfirst=True, fuzzy=True).date()
    except (ValueError, OverflowError):
        return None


def is_date_ambiguous(raw: str) -> bool:
    """True when both day and month components are <=12, making DD/MM vs MM/DD unclear."""
    parts = [p for p in raw.replace("-", "/").split("/") if p.isdigit()]
    if len(parts) < 2:
        return False
    a, b = int(parts[0]), int(parts[1])
    return a <= 12 and b <= 12 and a != b
