"""Copies all data from the RDS Postgres database into the local SQLite file, so the local
SQLite DB mirrors RDS. Read-only against RDS; the SQLite file is dropped and rebuilt.

Usage: python scripts/sync_rds_to_sqlite.py
"""
import sys

from sqlalchemy import create_engine, event, text

from app.core.config import get_settings
from app.database.session import Base, _generate_rds_iam_token
from app import models  # noqa: F401  (registers all model classes on Base.metadata)


def build_rds_engine(settings):
    url = (
        f"postgresql+psycopg2://{settings.RDS_USER}@{settings.RDS_HOST}:{settings.RDS_PORT}"
        f"/{settings.RDS_DB_NAME}"
    )
    engine = create_engine(url, pool_pre_ping=True, connect_args={"sslmode": "require"})

    @event.listens_for(engine, "do_connect")
    def _inject_iam_token(dialect, conn_rec, cargs, cparams):
        cparams["password"] = _generate_rds_iam_token()

    return engine


def main() -> int:
    settings = get_settings()
    if not settings.RDS_IAM_AUTH:
        print("RDS_IAM_AUTH is not enabled in settings; nothing to sync from.")
        return 1

    sqlite_url = settings.DATABASE_URL
    if not sqlite_url.startswith("sqlite"):
        print(f"DATABASE_URL ({sqlite_url}) is not a sqlite URL; refusing to overwrite it.")
        return 1

    print(f"Source (RDS): {settings.RDS_USER}@{settings.RDS_HOST}:{settings.RDS_PORT}/{settings.RDS_DB_NAME}")
    print(f"Target (SQLite): {sqlite_url}")

    rds_engine = build_rds_engine(settings)
    sqlite_engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

    with rds_engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("RDS connection OK.")

    # Rebuild the sqlite schema from scratch so it matches current models exactly.
    Base.metadata.drop_all(sqlite_engine)
    Base.metadata.create_all(sqlite_engine)
    print("SQLite schema (re)created.")

    tables = Base.metadata.sorted_tables  # dependency order (parents before children)
    with rds_engine.connect() as src, sqlite_engine.begin() as dst:
        for table in tables:
            rows = src.execute(table.select()).mappings().all()
            if rows:
                dst.execute(table.insert(), [dict(row) for row in rows])
            print(f"  {table.name}: {len(rows)} rows")

    print("Sync complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
