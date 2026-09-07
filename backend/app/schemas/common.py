"""Standard API response envelope used across all endpoints."""
from typing import Any, Optional


def success(data: Any = None, meta: Optional[dict] = None) -> dict:
    return {"success": True, "data": data, "meta": meta or {}}


def error(code: str, message: str, details: Any = None) -> dict:
    return {"success": False, "error": {"code": code, "message": message, "details": details}}
