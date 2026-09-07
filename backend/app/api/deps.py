"""Auth dependency: extracts and validates the current user from a Bearer token.
Every endpoint touching financial data must depend on get_current_user, never trust a
user_id or entity id supplied directly by the client."""
from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.security import decode_access_token
from app.database.session import get_db
from app.models.user import User


def get_current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    if not authorization.startswith("Bearer "):
        raise AppError(ErrorCode.UNAUTHORIZED, "Missing or invalid authorization header.", status_code=401)
    token = authorization.removeprefix("Bearer ").strip()
    user_id = decode_access_token(token)
    if not user_id:
        raise AppError(ErrorCode.UNAUTHORIZED, "Invalid or expired token.", status_code=401)
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise AppError(ErrorCode.UNAUTHORIZED, "User not found or inactive.", status_code=401)
    return user
