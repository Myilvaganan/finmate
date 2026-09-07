import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["AI_PROVIDER"] = "mock"

from app.database.session import Base, get_db
from app.main import app


@pytest.fixture()
def client(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )

    # SQLite doesn't enforce foreign keys unless told to -- enable it so these tests catch the
    # same FK-violation failures that only show up against a real database like Postgres/RDS.
    @event.listens_for(engine, "connect")
    def _enable_sqlite_fk(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Background tasks (statement ingestion) open their own SessionLocal() rather than going
    # through Depends(get_db), so they don't pick up the override above by default -- without
    # this patch they'd silently hit whichever real database is configured in .env (e.g. RDS)
    # instead of this test's in-memory SQLite.
    monkeypatch.setattr("app.workers.job_runner.SessionLocal", TestingSessionLocal)

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def signup(client, email="user1@test.com", password="password123"):
    resp = client.post("/api/auth/signup", json={"email": email, "password": password, "full_name": "Test User"})
    return resp.json()["data"]["token"]
