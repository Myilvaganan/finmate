import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import AppError, ErrorCode
from app.database.session import get_db
from app.models.job import UploadJob
from app.models.user import User
from app.schemas.common import success

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}")
def get_job(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.get(UploadJob, job_id)
    if not job or job.user_id != user.id:
        raise AppError(ErrorCode.NOT_FOUND, "Job not found.", status_code=404)
    return success({
        "id": job.id, "status": job.status, "progress": job.progress,
        "statement_id": job.statement_id, "error_message": job.error_message,
        "result": json.loads(job.result_json) if job.result_json else None,
    })
