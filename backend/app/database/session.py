"""SQLAlchemy engine/session setup. DATABASE_URL can be swapped to PostgreSQL without code changes
elsewhere. Optionally supports AWS RDS IAM authentication (see RDS_IAM_AUTH in core/config.py)."""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


def _generate_rds_iam_token() -> str:
    import boto3

    client = boto3.client("rds", region_name=settings.AWS_REGION)
    return client.generate_db_auth_token(
        DBHostname=settings.RDS_HOST, Port=settings.RDS_PORT, DBUsername=settings.RDS_USER,
    )


def _build_engine():
    if settings.RDS_IAM_AUTH:
        # No password lives in the connection string -- a fresh IAM token is generated for
        # every new physical connection. pool_recycle forces the pool to periodically drop and
        # reopen connections so a token can never be used past its ~15 minute validity window.
        url = (
            f"postgresql+psycopg2://{settings.RDS_USER}@{settings.RDS_HOST}:{settings.RDS_PORT}"
            f"/{settings.RDS_DB_NAME}"
        )
        engine = create_engine(
            url, pool_pre_ping=True, pool_recycle=300, connect_args={"sslmode": "require"},
        )

        @event.listens_for(engine, "do_connect")
        def _inject_iam_token(dialect, conn_rec, cargs, cparams):
            cparams["password"] = _generate_rds_iam_token()

        logger.info("Database engine using RDS IAM authentication (host=%s db=%s)", settings.RDS_HOST, settings.RDS_DB_NAME)
        return engine

    is_sqlite = settings.DATABASE_URL.startswith("sqlite")
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    # pool_pre_ping avoids "server closed the connection unexpectedly" errors against a networked
    # database (e.g. RDS) whose connections can be dropped by an idle timeout or failover.
    return create_engine(settings.DATABASE_URL, connect_args=connect_args, pool_pre_ping=not is_sqlite)


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
