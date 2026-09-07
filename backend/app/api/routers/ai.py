from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.ai.chat_service import route_question
from app.ai.factory import get_ai_provider
from app.api.deps import get_current_user
from app.core.errors import AppError, ErrorCode
from app.database.session import get_db
from app.models.chat import ChatMessage, ChatSession
from app.models.user import User
from app.schemas.common import success

router = APIRouter(prefix="/api/ai", tags=["ai"])


class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None


@router.post("/chat")
def chat(payload: ChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = None
    if payload.session_id:
        session = db.get(ChatSession, payload.session_id)
        if not session or session.user_id != user.id:
            raise AppError(ErrorCode.NOT_FOUND, "Chat session not found.", status_code=404)
    if not session:
        session = ChatSession(user_id=user.id, title=payload.question[:60])
        db.add(session)
        db.flush()

    db.add(ChatMessage(session_id=session.id, role="user", content=payload.question))

    provider = get_ai_provider()
    answer = route_question(db, user.id, payload.question, provider)

    import json
    db.add(ChatMessage(
        session_id=session.id, role="assistant", content=answer.text,
        structured_data_json=json.dumps(answer.structured_data, default=str),
    ))
    db.commit()

    return success({
        "session_id": session.id, "answer": answer.text, "fact_type": answer.fact_type,
        "structured_data": answer.structured_data, "ai_available": provider.is_available,
        "disclaimer": "FinMate provides insights based on your transaction data and is not a substitute for professional financial advice.",
    })


@router.get("/sessions")
def list_sessions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sessions = db.query(ChatSession).filter(ChatSession.user_id == user.id).order_by(ChatSession.created_at.desc()).all()
    return success([{"id": s.id, "title": s.title, "created_at": s.created_at.isoformat()} for s in sessions])


@router.get("/sessions/{session_id}")
def get_session(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.get(ChatSession, session_id)
    if not session or session.user_id != user.id:
        raise AppError(ErrorCode.NOT_FOUND, "Chat session not found.", status_code=404)
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at).all()
    return success({
        "id": session.id, "title": session.title,
        "messages": [{"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()} for m in messages],
    })
