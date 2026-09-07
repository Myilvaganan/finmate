import json

from fastapi import APIRouter, BackgroundTasks, Depends, Form
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import AppError, ErrorCode
from app.database.session import get_db
from app.models.job import UploadJob
from app.models.user import User
from app.schemas.common import success
from app.workers.job_runner import run_statement_ingestion

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _parse_error(error_message: str | None) -> dict:
    if not error_message:
        return {"code": None, "message": None}
    try:
        parsed = json.loads(error_message)
        return {"code": parsed.get("code"), "message": parsed.get("message")}
    except (json.JSONDecodeError, TypeError):
        return {"code": None, "message": error_message}


@router.get("/{job_id}")
def get_job(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.get(UploadJob, job_id)
    if not job or job.user_id != user.id:
        raise AppError(ErrorCode.NOT_FOUND, "Job not found.", status_code=404)
    error = _parse_error(job.error_message)
    return success({
        "id": job.id, "status": job.status, "progress": job.progress,
        "statement_id": job.statement_id, "error_code": error["code"], "error_message": error["message"],
        "result": json.loads(job.result_json) if job.result_json else None,
    })


@router.post("/{job_id}/retry")
def retry_job(
    job_id: str, background_tasks: BackgroundTasks, password: str = Form(...),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    job = db.get(UploadJob, job_id)
    if not job or job.user_id != user.id:
        raise AppError(ErrorCode.NOT_FOUND, "Job not found.", status_code=404)

    try:
        parsed = json.loads(job.error_message) if job.error_message else {}
    except json.JSONDecodeError:
        parsed = {}
    retry_context = parsed.get("retry_context")
    if not retry_context:
        raise AppError(ErrorCode.VALIDATION_ERROR, "This job has no pending retry (the file may have already been processed or discarded).")

    job.status = "QUEUED"
    job.progress = 0
    job.error_message = None
    db.commit()

    background_tasks.add_task(
        run_statement_ingestion, job.id, user.id,
        retry_context["file_path"], retry_context["original_filename"], retry_context["file_format"],
        password,
    )
    return success({"job_id": job.id, "status": job.status})
