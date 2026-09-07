"""Regression test for deleting an account/statement that still has dependent rows -- this only
failed against a real foreign-key-enforcing database (Postgres/RDS), not the old unconstrained
SQLite test setup, so conftest.py now enables SQLite's FK pragma to catch this class of bug."""
from tests.conftest import signup


def _upload_and_confirm_statement(client, token):
    csv_content = (
        "Date,Description,Debit,Credit,Balance\n"
        "01/08/2026,SALARY CREDIT,,50000,50000\n"
        "02/08/2026,SWIGGY ORDER,500,,49500\n"
    )
    resp = client.post(
        "/api/statements/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test.csv", csv_content, "text/csv")},
    )
    job_id = resp.json()["data"]["job_id"]
    # BackgroundTasks run synchronously within TestClient's request cycle, so the job is
    # already finished (or failed) by the time this call returns.
    job = client.get(f"/api/jobs/{job_id}", headers={"Authorization": f"Bearer {token}"}).json()["data"]
    statement_id = job["statement_id"]
    assert statement_id, f"Statement ingestion did not complete: {job}"
    client.post(f"/api/statements/{statement_id}/confirm", headers={"Authorization": f"Bearer {token}"})
    return statement_id


def test_delete_account_with_statements_and_transactions(client):
    token = signup(client, "deleteacct@test.com", "password123")
    _upload_and_confirm_statement(client, token)

    accounts = client.get("/api/accounts", headers={"Authorization": f"Bearer {token}"}).json()["data"]
    assert len(accounts) == 1
    account_id = accounts[0]["id"]

    resp = client.delete(f"/api/accounts/{account_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.json()
    assert resp.json()["data"]["deleted"] is True

    remaining = client.get("/api/accounts", headers={"Authorization": f"Bearer {token}"}).json()["data"]
    assert remaining == []


def test_delete_statement_with_transactions(client):
    token = signup(client, "deletestmt@test.com", "password123")
    statement_id = _upload_and_confirm_statement(client, token)

    resp = client.delete(f"/api/statements/{statement_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.json()
    assert resp.json()["data"]["transactions_deleted"] == 2

    txns = client.get("/api/transactions", headers={"Authorization": f"Bearer {token}"}).json()["data"]
    assert txns == []

    # Balance must not stay stale once its only source transactions are gone.
    accounts = client.get("/api/accounts", headers={"Authorization": f"Bearer {token}"}).json()["data"]
    assert accounts[0]["closing_balance"] == 0.0
    assert accounts[0]["opening_balance"] == 0.0


def test_account_balance_reflects_latest_transaction_after_import(client):
    token = signup(client, "balancecheck@test.com", "password123")
    _upload_and_confirm_statement(client, token)

    accounts = client.get("/api/accounts", headers={"Authorization": f"Bearer {token}"}).json()["data"]
    assert accounts[0]["closing_balance"] == 49500.0
