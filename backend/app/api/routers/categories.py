from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import AppError, ErrorCode
from app.database.session import get_db
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.common import success

router = APIRouter(prefix="/api/categories", tags=["categories"])


def _serialize(c: Category) -> dict:
    return {
        "id": c.id, "name": c.name, "parent_type": c.parent_type, "group_name": c.group_name,
        "is_essential": c.is_essential, "is_system": c.is_system,
    }


@router.get("")
def list_categories(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # System categories (user_id is null) plus this user's own custom ones.
    categories = db.query(Category).filter(
        (Category.user_id.is_(None)) | (Category.user_id == user.id)
    ).order_by(Category.group_name, Category.name).all()
    return success([_serialize(c) for c in categories])


class CategoryCreate(BaseModel):
    name: str
    group_name: Optional[str] = None
    parent_type: str = "expense"
    is_essential: bool = False


@router.post("")
def create_category(
    payload: CategoryCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    name = payload.name.strip()
    if not name:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Category name is required.")
    if payload.parent_type not in ("income", "expense", "transfer", "investment"):
        raise AppError(ErrorCode.VALIDATION_ERROR, "Invalid parent_type.")
    existing = db.query(Category).filter(
        (Category.user_id.is_(None)) | (Category.user_id == user.id), Category.name == name,
    ).first()
    if existing:
        raise AppError(ErrorCode.VALIDATION_ERROR, "A category with this name already exists.")

    category = Category(
        user_id=user.id, name=name, parent_type=payload.parent_type,
        group_name=payload.group_name or name, is_essential=payload.is_essential, is_system=False,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return success(_serialize(category))


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    group_name: Optional[str] = None
    is_essential: Optional[bool] = None


def _get_owned_category(db: Session, category_id: str, user_id: str) -> Category:
    category = db.get(Category, category_id)
    if not category or category.user_id != user_id:
        raise AppError(ErrorCode.NOT_FOUND, "Category not found.", status_code=404)
    return category


@router.patch("/{category_id}")
def update_category(
    category_id: str, payload: CategoryUpdate,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    category = _get_owned_category(db, category_id, user.id)
    if payload.name is not None:
        category.name = payload.name.strip() or category.name
    if payload.group_name is not None:
        category.group_name = payload.group_name
    if payload.is_essential is not None:
        category.is_essential = payload.is_essential
    db.commit()
    db.refresh(category)
    return success(_serialize(category))


@router.delete("/{category_id}")
def delete_category(category_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    category = _get_owned_category(db, category_id, user.id)
    in_use = db.query(Transaction).filter(Transaction.category_id == category_id).first()
    if in_use:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            "This category is still assigned to transactions -- recategorize them first.",
        )
    db.delete(category)
    db.commit()
    return success({"deleted": True})
