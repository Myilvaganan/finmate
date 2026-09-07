"""ParserRegistry: detects the right parser for a given file and format hint."""
from pathlib import Path
from typing import List

from app.parsers.base import BaseStatementParser
from app.parsers.csv_parser import CSVStatementParser
from app.parsers.excel_parser import ExcelStatementParser
from app.parsers.txt_parser import TXTStatementParser
from app.parsers.html_parser import HTMLStatementParser
from app.parsers.pdf_parser import PDFStatementParser
from app.parsers.ocr_parser import OCRStatementParser
from app.parsers.generic_parser import GenericStatementParser


class ParserRegistry:
    def __init__(self) -> None:
        self._parsers: List[BaseStatementParser] = [
            CSVStatementParser(),
            ExcelStatementParser(),
            TXTStatementParser(),
            HTMLStatementParser(),
            PDFStatementParser(),
            OCRStatementParser(),
        ]
        self._fallback = GenericStatementParser()

    def detect_parser(self, filename: str, sample: bytes) -> BaseStatementParser:
        for parser in self._parsers:
            if parser.can_parse(filename, sample):
                return parser
        return self._fallback


registry = ParserRegistry()
