"""
Tests for accountability: only admins may delete, and the activity log is
admin-only.
"""

PART = {"part_number": "ACT-1", "name": "Audit Part", "category": "Misc",
        "stock_quantity": 5, "unit_price": 10.0}


def _employee_headers(client, auth_headers, username="emp1"):
    client.post(
        "/api/auth/register",
        json={"username": username, "full_name": "Employee", "password": "passord123", "role": "ansatt"},
        headers=auth_headers,
    )
    r = client.post("/api/auth/login", data={"username": username, "password": "passord123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_employee_cannot_delete_part(client, auth_headers):
    part = client.post("/api/parts/", json=PART, headers=auth_headers).json()
    emp = _employee_headers(client, auth_headers)
    r = client.delete(f"/api/parts/{part['id']}", headers=emp)
    assert r.status_code == 403
    assert "admin" in r.json()["detail"].lower()
    # the part is still there
    assert client.get(f"/api/parts/{part['id']}", headers=auth_headers).status_code == 200


def test_admin_can_delete_part(client, auth_headers):
    part = client.post("/api/parts/", json={**PART, "part_number": "ACT-2"}, headers=auth_headers).json()
    assert client.delete(f"/api/parts/{part['id']}", headers=auth_headers).status_code == 204


def test_employee_cannot_delete_order(client, auth_headers):
    part = client.post("/api/parts/", json={**PART, "part_number": "ACT-3"}, headers=auth_headers).json()
    order = client.post(
        "/api/orders/",
        json={"customer_id": 1, "part_id": part["id"], "quantity": 1},
        headers=auth_headers,
    ).json()
    emp = _employee_headers(client, auth_headers, username="emp2")
    r = client.delete(f"/api/orders/{order['id']}", headers=emp)
    assert r.status_code == 403


def test_activity_log_is_admin_only(client, auth_headers):
    assert client.get("/api/activity/", headers=auth_headers).status_code == 200
    emp = _employee_headers(client, auth_headers, username="emp3")
    assert client.get("/api/activity/", headers=emp).status_code == 403
