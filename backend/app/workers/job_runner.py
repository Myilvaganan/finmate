"""Background job execution for statement processing.

This runs on FastAPI's BackgroundTasks (a simple, reliable in-process worker suitable for a
single-server deployment). The pipeline and job-status contract are designed so this function
body can move unchanged into a Celery/RQ/SQS task later -- callers only depend on UploadJob rows.
"""
import json
import traceback
from pathlib import Path
from typing import Optional

from app.core.logging import get_logger
from app.database.session import SessionLocal
from app.models.job import UploadJob
from app.models.statement import StatementProcessingError
from app.core.errors import AppError
from app.services.statement_import import StatementImportService
from app.utils.files import delete_temp_file

logger = get_logger(__name__)

STAGES = [
    ("EXTRACTING", 20), ("NORMALIZING", 40), ("VALIDATING", 55),
    ("CHECKING_DUPLICATES", 70), ("CATEGORIZING", 85), ("SAVING", 95),
]


def run_statement_ingestion(
    job_id: str, user_id: str, file_path: str, original_filename: str, file_format: str,
    password: Optional[str] = None,
) -> None:
    db = SessionLocal()
    # A password-required/incorrect PDF isn't a failed upload in the usual sense -- the file
    # is kept so the frontend can resubmit the same job with a password without re-uploading.
    keep_file = False
    try:
        job = db.get(UploadJob, job_id)
        if not job:
            return

        job.status = "EXTRACTING"
        job.progress = 20
        db.commit()

        service = StatementImportService(db)
        try:
            job.status = "CATEGORIZING"
            job.progress = 80
            db.commit()

            summary = service.ingest(user_id, file_path, original_filename, file_format, password)

            # Processing always lands in NEEDS_REVIEW: the user must confirm the import
            # (see POST /api/statements/{id}/confirm) even when there are no conflicts,
            # per the mandatory Import Review screen.
            job.status = "NEEDS_REVIEW"
            job.progress = 100
            job.statement_id = summary.statement_id
            job.result_json = json.dumps(summary.__dict__)
        except AppError as exc:
            logger.warning("Statement ingestion failed [job=%s stage=processing]: %s", job_id, exc.code)
            job.status = "FAILED"
            job.error_message = json.dumps({"code": exc.code, "message": exc.message})
            if exc.code in ("PDF_PASSWORD_REQUIRED", "PDF_PASSWORD_INCORRECT"):
                keep_file = True
                job.error_message = json.dumps({
                    "code": exc.code, "message": exc.message,
                    "retry_context": {
                        "file_path": file_path, "original_filename": original_filename, "file_format": file_format,
                    },
                })
            db.add(StatementProcessingError(
                statement_id=job.statement_id or "unknown", stage="ingest", error_code=exc.code, message=exc.message,
            )) if job.statement_id else None
        except Exception as exc:
            logger.exception("Unexpected failure during statement ingestion [job=%s]", job_id)
            job.status = "FAILED"
            job.error_message = json.dumps({"code": "DATABASE_ERROR", "message": "An unexpected error occurred while processing this statement."})

        db.commit()
    finally:
        if not keep_file:
            delete_temp_file(Path(file_path))
        db.close()
