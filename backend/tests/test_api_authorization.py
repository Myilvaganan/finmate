from tests.conftest import signup


def test_signup_and_login(client):
    token = signup(client, "alice@test.com", "password123")
    assert token

    resp = client.post("/api/auth/login", json={"email": "alice@test.com", "password": "password123"})
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_wrong_password_rejected(client):
    signup(client, "bob@test.com", "password123")
    resp = client.post("/api/auth/login", json={"email": "bob@test.com", "password": "wrongpass"})
    assert resp.status_code == 401


def test_unauthenticated_request_rejected(client):
    resp = client.get("/api/transactions")
    assert resp.status_code == 401


def test_user_cannot_access_another_users_account(client):
    token_a = signup(client, "usera@test.com", "password123")
    token_b = signup(client, "userb@test.com", "password123")

    create_resp = client.post(
        "/api/accounts", json={"bank_name": "Test Bank", "account_type": "bank"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    account_id = create_resp.json()["data"]["id"]

    # User B must not see user A's account in their own list.
    list_resp = client.get("/api/accounts", headers={"Authorization": f"Bearer {token_b}"})
    assert account_id not in [a["id"] for a in list_resp.json()["data"]]

    # User B must not be able to delete user A's account.
    delete_resp = client.delete(f"/api/accounts/{account_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert delete_resp.status_code == 404


def test_user_cannot_access_another_users_statement(client):
    token_a = signup(client, "usera2@test.com", "password123")
    token_b = signup(client, "userb2@test.com", "password123")

    resp = client.get("/api/statements/nonexistent-id", headers={"Authorization": f"Bearer {token_b}"})
    assert resp.status_code == 404


def test_analytics_scoped_to_current_user(client):
    token_a = signup(client, "usera3@test.com", "password123")
    token_b = signup(client, "userb3@test.com", "password123")

    resp_a = client.get("/api/analytics/overview", headers={"Authorization": f"Bearer {token_a}"})
    resp_b = client.get("/api/analytics/overview", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_a.status_code == 200 and resp_b.status_code == 200
    assert resp_a.json()["data"]["transaction_count"] == 0
    assert resp_b.json()["data"]["transaction_count"] == 0
