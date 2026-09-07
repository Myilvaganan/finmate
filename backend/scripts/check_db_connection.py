"""Verifies the configured database (SQLite, plain Postgres, or RDS IAM auth) is reachable
before running migrations against it.

Usage: python scripts/check_db_connection.py
"""
import sys

from sqlalchemy import text

from app.core.config import get_settings
from app.database.session import engine


def main() -> int:
    settings = get_settings()
    if settings.RDS_IAM_AUTH:
        print(f"Connecting via RDS IAM auth to {settings.RDS_USER}@{settings.RDS_HOST}:{settings.RDS_PORT}/{settings.RDS_DB_NAME} ...")
    else:
        safe_url = settings.DATABASE_URL
        if "@" in safe_url and "://" in safe_url:
            scheme, rest = safe_url.split("://", 1)
            creds, host = rest.split("@", 1)
            user = creds.split(":", 1)[0]
            safe_url = f"{scheme}://{user}:***@{host}"
        print(f"Connecting to {safe_url} ...")

    try:
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version()")).scalar() if not settings.DATABASE_URL.startswith("sqlite") or settings.RDS_IAM_AUTH else "sqlite"
        print(f"Connection succeeded. Server: {version}")
        return 0
    except Exception as exc:
        print(f"Connection FAILED: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
