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


def test_login_rate_limited_after_repeated_failures(client):
    # Unique username so this doesn't interfere with other tests' throttle state
    creds = {"username": "bruteforce_target", "password": "wrong"}
    for _ in range(5):
        assert client.post("/api/auth/login", data=creds).status_code == 401
    # The 6th attempt within the window is blocked
    blocked = client.post("/api/auth/login", data=creds)
    assert blocked.status_code == 429
