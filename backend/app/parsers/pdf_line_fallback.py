"""Fallback extraction for PDF statements where transactions don't form a clean pdfplumber
table -- common in Indian bank layouts (e.g. ICICI) where each transaction's remarks wrap
across several lines with the date/amount line interleaved partway through the wrap.

Layout this handles (verified against real ICICI/Axis exports): the header itself is usually
split across several short lines ("Transaction" / "S No. Cheque Number Transaction Remarks" /
"Date Amount (INR) ..."), so header detection can't require one line with date+description+
balance all together -- it instead requires all three keywords to appear somewhere in a
rolling window of recent lines.

Each transaction then looks like:
    <first line of the remarks text>
    <serial no> <date> <amount> [<amount>]      <- the anchor line
    <remaining lines of the remarks text>
    <first line of the NEXT transaction's remarks text>
    ...next anchor...

i.e. exactly one remarks line precedes each anchor and the rest follow it -- so a
transaction's full description is only known once the *next* anchor's preceding line has
been split off. Since we don't have a reliable deposit vs. withdrawal column at that point,
direction is inferred from whether the running balance increased or decreased -- which is
exactly what a human reading the statement would do too.
"""
import re
from collections import deque
from typing import Deque, List, Optional

from app.parsers.base import RawTransactionRow

_HEADER_DATE_RE = re.compile(r"\bdate\b", re.I)
_HEADER_DESC_RE = re.compile(r"\b(particulars|narration|remarks|description)\b", re.I)
_HEADER_BALANCE_RE = re.compile(r"\bbalance\b", re.I)
_HEADER_WINDOW = 6

# Optional leading serial number (e.g. ICICI's "S No." column), then a date with '/', '-' or '.'
# separators (Indian statements use all three depending on the bank).
_ANCHOR_RE = re.compile(r"^(?:\d+\s+)?(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})\s+(.*)$")
_AMOUNT_RE = re.compile(r"[\d,]+\.\d{2}")
_JUNK_LINE_RE = re.compile(
    r"^(Page\s+\d+\s+of\s+\d+|Total:?\b|Note:|Sincer(e|ly)|Team\s|This is a system generated|Legends?\s+for)",
    re.I,
)


def _parse_amount(raw: str) -> float:
    return float(raw.replace(",", ""))


def extract_rows_from_text(full_text: str) -> List[RawTransactionRow]:
    rows: List[RawTransactionRow] = []
    seen_header = False
    header_window: Deque[str] = deque(maxlen=_HEADER_WINDOW)

    buffer: List[str] = []  # lines seen since the last anchor
    prev_balance: Optional[float] = None
    pending: Optional[dict] = None  # the most recent anchor, awaiting its trailing description lines
    row_index = 0

    def finalize_pending(trailing_lines: List[str]) -> None:
        nonlocal row_index
        if pending is None:
            return
        description = " ".join(pending["prefix"] + trailing_lines).strip() or "(no description)"
        rows.append(RawTransactionRow(
            row_index=row_index,
            transaction_date_raw=pending["date_raw"],
            description_raw=description,
            debit_raw=pending["debit_raw"],
            credit_raw=pending["credit_raw"],
            balance_raw=pending["balance_raw"],
        ))
        row_index += 1

    for raw_line in full_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if not seen_header:
            header_window.append(line)
            joined = " ".join(header_window)
            if (
                _HEADER_DATE_RE.search(joined)
                and _HEADER_DESC_RE.search(joined)
                and _HEADER_BALANCE_RE.search(joined)
            ):
                seen_header = True
                header_window.clear()
                buffer = []
            continue

        if _JUNK_LINE_RE.match(line):
            finalize_pending(buffer)
            pending = None
            buffer = []
            continue

        match = _ANCHOR_RE.match(line)
        if not match:
            buffer.append(line)
            continue

        date_raw, rest = match.group(1), match.group(2)
        amounts = _AMOUNT_RE.findall(rest)

        # The line immediately before this anchor belongs to *this* transaction's description;
        # everything earlier in the buffer is trailing description for the *previous* one.
        anchor_prefix = buffer[-1:] if buffer else []
        prior_trailing = buffer[:-1] if buffer else []
        finalize_pending(prior_trailing)
        buffer = []

        if len(amounts) <= 1:
            # Opening/closing balance line (e.g. "01-08-2026 B/F 2,18,656.99") -- not a
            # transaction, but its balance still anchors credit/debit inference for what follows.
            if amounts:
                prev_balance = _parse_amount(amounts[-1])
            pending = None
            continue

        amount_raw, balance_raw = amounts[0], amounts[-1]
        balance_val = _parse_amount(balance_raw)
        is_credit = prev_balance is not None and balance_val > prev_balance
        prev_balance = balance_val

        pending = {
            "prefix": anchor_prefix,
            "date_raw": date_raw,
            "debit_raw": "" if is_credit else amount_raw,
            "credit_raw": amount_raw if is_credit else "",
            "balance_raw": balance_raw,
        }

    finalize_pending(buffer)
    return rows
