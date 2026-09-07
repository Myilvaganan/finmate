"""OCR-based parser for scanned statement images. Degrades gracefully if tesseract isn't installed."""
import re
from typing import Optional

from app.parsers.base import BaseStatementParser, NormalizedStatement, RawTransactionRow
from app.parsers.bank_detection import (
    detect_bank_from_text, detect_account_type, detect_currency, detect_account_identifier,
)
from app.core.errors import AppError, ErrorCode

_LINE_RE = re.compile(
    r"(?P<date>\d{1,2}[/\-][A-Za-z0-9]{2,4}[/\-]\d{2,4})\s+"
    r"(?P<desc>.+?)\s+"
    r"(?P<amount>[\d,]+\.\d{2})\s*(?P<type>DR|CR)?$",
    re.I,
)


def _extract_text(file_path: str) -> Optional[str]:
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return None
    try:
        return pytesseract.image_to_string(Image.open(file_path))
    except Exception:
        return None


class OCRStatementParser(BaseStatementParser):
    format_name = "ocr"

    def can_parse(self, filename: str, sample: bytes) -> bool:
        return filename.lower().endswith((".png", ".jpg", ".jpeg"))

    def parse(self, file_path: str, password: Optional[str] = None) -> NormalizedStatement:
        text = _extract_text(file_path)
        if text is None:
            raise AppError(
                ErrorCode.PARSER_FAILED,
                "OCR is not available on this server (tesseract not installed). "
                "Please upload a PDF/CSV/XLSX statement instead.",
            )

        rows = []
        for i, line in enumerate(text.splitlines()):
            match = _LINE_RE.search(line.strip())
            if not match:
                continue
            amount = match.group("amount")
            kind = (match.group("type") or "").upper()
            rows.append(
                RawTransactionRow(
                    row_index=i,
                    transaction_date_raw=match.group("date"),
                    description_raw=match.group("desc").strip(),
                    debit_raw=amount if kind == "DR" else "",
                    credit_raw=amount if kind == "CR" else "",
                )
            )

        if not rows:
            raise AppError(
                ErrorCode.NO_TRANSACTIONS_FOUND,
                "OCR could not detect transaction lines in this image. Try a clearer scan.",
            )

        return NormalizedStatement(
            bank_name=detect_bank_from_text(text),
            account_type=detect_account_type(text),
            currency=detect_currency(text),
            account_identifier=detect_account_identifier(text),
            period_start=None,
            period_end=None,
            period_confidence=0.0,
            parser_used=self.format_name,
            rows=rows,
            warnings=["Parsed via OCR — accuracy may be lower than digital formats. Please review carefully."],
        )
