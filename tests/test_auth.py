"""
Tester for autentisering og JWT-håndtering.
"""


def test_login_success(client):
    response = client.post(
        "/api/auth/login",
        data={"username": "testadmin", "password": "testpass"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == "admin"


def test_login_wrong_password(client):
    response = client.post(
        "/api/auth/login",
        data={"username": "testadmin", "password": "feil_passord"},
    )
    assert response.status_code == 401


def test_login_unknown_user(client):
    response = client.post(
        "/api/auth/login",
        data={"username": "finnesikke", "password": "noe"},
    )
    assert response.status_code == 401


def test_get_me(client, auth_headers):
    response = client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testadmin"
    assert data["role"] == "admin"


def test_register_new_user_as_admin(client, auth_headers):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "ny_ansatt",
            "full_name": "Ny Ansatt",
            "password": "passord123",
            "role": "ansatt",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert "created" in response.json()["message"]


def test_invalid_token(client):
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer ugyldig_token"})
    assert response.status_code == 401


def _create_employee(client, auth_headers, username="100724"):
    return client.post(
        "/api/auth/register",
        json={"username": username, "full_name": "Test Employee", "password": "passord123", "role": "ansatt"},
        headers=auth_headers,
    )


def test_admin_can_deactivate_and_reactivate_user(client, auth_headers):
    _create_employee(client, auth_headers)
    users = client.get("/api/auth/users?include_inactive=true", headers=auth_headers).json()
    emp = next(u for u in users if u["username"] == "100724")
    assert emp["is_active"] is True

    # Deactivate
    r = client.put(f"/api/auth/users/{emp['id']}", json={"is_active": False}, headers=auth_headers)
    assert r.status_code == 200
    # Disabled user no longer appears in the default (active-only) list
    active = client.get("/api/auth/users", headers=auth_headers).json()
    assert all(u["username"] != "100724" for u in active)
    # …but shows when including inactive
    allu = client.get("/api/auth/users?include_inactive=true", headers=auth_headers).json()
    assert any(u["username"] == "100724" and u["is_active"] is False for u in allu)

    # Reactivate
    client.put(f"/api/auth/users/{emp['id']}", json={"is_active": True}, headers=auth_headers)
    active = client.get("/api/auth/users", headers=auth_headers).json()
    assert any(u["username"] == "100724" for u in active)


def test_admin_cannot_deactivate_self(client, auth_headers):
    me = client.get("/api/auth/me", headers=auth_headers).json()
    r = client.put(f"/api/auth/users/{me['id']}", json={"is_active": False}, headers=auth_headers)
    assert r.status_code == 400
    assert "your own account" in r.json()["detail"]


def test_update_user_rejects_invalid_role(client, auth_headers):
    resp = _create_employee(client, auth_headers, username="100725")
    assert resp.status_code == 201
    users = client.get("/api/auth/users?include_inactive=true", headers=auth_headers).json()
    emp = next(u for u in users if u["username"] == "100725")
    r = client.put(f"/api/auth/users/{emp['id']}", json={"role": "superuser"}, headers=auth_headers)
    assert r.status_code == 400
    assert "Invalid role" in r.json()["detail"]


def test_admin_can_change_user_password(client, auth_headers):
    client.post(
        "/api/auth/register",
        json={"username": "pwuser", "full_name": "PW User", "password": "oldpass123", "role": "ansatt"},
        headers=auth_headers,
    )
    users = client.get("/api/auth/users?include_inactive=true", headers=auth_headers).json()
    u = next(x for x in users if x["username"] == "pwuser")

    # Too short → rejected
    short = client.put(f"/api/auth/users/{u['id']}", json={"password": "12"}, headers=auth_headers)
    assert short.status_code == 400

    # Valid change → old password stops working, new one works
    r = client.put(f"/api/auth/users/{u['id']}", json={"password": "newpass123"}, headers=auth_headers)
    assert r.status_code == 200
    assert client.post("/api/auth/login", data={"username": "pwuser", "password": "oldpass123"}).status_code == 401
    assert client.post("/api/auth/login", data={"username": "pwuser", "password": "newpass123"}).status_code == 200


def test_login_rate_limited_after_repeated_failures(client):
    # Unique username so this doesn't interfere with other tests' throttle state
    creds = {"username": "bruteforce_target", "password": "wrong"}
    for _ in range(5):
        assert client.post("/api/auth/login", data=creds).status_code == 401
    # The 6th attempt within the window is blocked
    blocked = client.post("/api/auth/login", data=creds)
    assert blocked.status_code == 429
