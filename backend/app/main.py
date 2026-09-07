from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.api.routers import accounts, ai, analytics, auth, jobs, reports, statements, transactions
from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode
from app.core.logging import get_logger
from app.database.session import Base, engine
from app import models  # noqa: F401  (ensures all models are registered on Base)

settings = get_settings()
logger = get_logger(__name__)

app = FastAPI(title=settings.APP_NAME, description=settings.APP_TAGLINE)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    # SQLite dev bootstrap; production deployments should run `alembic upgrade head` instead.
    Base.metadata.create_all(bind=engine)


@app.exception_handler(AppError)
def handle_app_error(request: Request, exc: AppError):
    logger.warning("AppError %s: %s", exc.code, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )


@app.exception_handler(RequestValidationError)
def handle_validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"success": False, "error": {"code": ErrorCode.VALIDATION_ERROR, "message": "Invalid request.", "details": exc.errors()}},
    )


@app.exception_handler(Exception)
def handle_unexpected_error(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": {"code": ErrorCode.DATABASE_ERROR, "message": "An unexpected error occurred.", "details": None}},
    )


app.include_router(auth.router)
app.include_router(statements.router)
app.include_router(transactions.router)
app.include_router(accounts.router)
app.include_router(analytics.router)
app.include_router(ai.router)
app.include_router(jobs.router)
app.include_router(reports.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME, "ai_provider": settings.AI_PROVIDER}
