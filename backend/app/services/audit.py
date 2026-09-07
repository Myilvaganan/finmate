import json
from typing import Optional

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def record_audit(db: Session, user_id: str, action: str, entity: str, entity_id: Optional[str] = None, metadata: Optional[dict] = None) -> None:
    db.add(AuditLog(
        user_id=user_id, action=action, entity=entity, entity_id=entity_id,
        metadata_json=json.dumps(metadata) if metadata else None,
    ))
    db.commit()
