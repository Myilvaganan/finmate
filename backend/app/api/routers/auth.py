from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.security import create_access_token, hash_password, verify_password
from app.database.session import get_db
from app.models.user import User
from app.schemas.common import success
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/signup")
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise AppError(ErrorCode.VALIDATION_ERROR, "An account with this email already exists.")
    if len(payload.password) < 8:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Password must be at least 8 characters.")

    user = User(email=payload.email, hashed_password=hash_password(payload.password), full_name=payload.full_name)
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return success({"token": token, "user": {"id": user.id, "email": user.email, "full_name": user.full_name, "plan": user.plan}})


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise AppError(ErrorCode.UNAUTHORIZED, "Invalid email or password.", status_code=401)

    token = create_access_token(user.id)
    return success({"token": token, "user": {"id": user.id, "email": user.email, "full_name": user.full_name, "plan": user.plan}})


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return success({"id": user.id, "email": user.email, "full_name": user.full_name, "plan": user.plan})
