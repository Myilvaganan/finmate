"""Standardized API error codes and exception type."""
from typing import Any, Optional


class ErrorCode:
    INVALID_FILE = "INVALID_FILE"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    PARSER_FAILED = "PARSER_FAILED"
    NO_TRANSACTIONS_FOUND = "NO_TRANSACTIONS_FOUND"
    DATE_DETECTION_FAILED = "DATE_DETECTION_FAILED"
    OVERLAPPING_STATEMENT = "OVERLAPPING_STATEMENT"
    DUPLICATE_STATEMENT = "DUPLICATE_STATEMENT"
    BALANCE_MISMATCH = "BALANCE_MISMATCH"
    AI_UNAVAILABLE = "AI_UNAVAILABLE"
    DATABASE_ERROR = "DATABASE_ERROR"
    NOT_FOUND = "NOT_FOUND"
    FORBIDDEN = "FORBIDDEN"
    UNAUTHORIZED = "UNAUTHORIZED"
    VALIDATION_ERROR = "VALIDATION_ERROR"


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, details: Optional[Any] = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)
