"""
Tester for reservedeler-API (CRUD og søk).
"""

import pytest


SAMPLE_PART = {
    "part_number": "TEST-001",
    "name": "Test Bremseklosser",
    "description": "Testbeskrivelse",
    "category": "Brakes",
    "compatible_cars": [{"make": "Toyota", "model": "Corolla", "year_from": 2010, "year_to": 2022}],
    "stock_quantity": 10,
    "ordered_quantity": 5,
    "loaned_quantity": 1,
    "low_stock_threshold": 3,
    "unit_price": 799.0,
    "location": "Reol A, Hylle 01",
}


def test_create_part(client, auth_headers):
    response = client.post("/api/parts/", json=SAMPLE_PART, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["part_number"] == "TEST-001"
    assert data["stock_status"] == "OK"
    assert data["available_quantity"] == 9  # 10 - 1 utlån


def test_create_duplicate_part_number(client, auth_headers):
    client.post("/api/parts/", json=SAMPLE_PART, headers=auth_headers)
    response = client.post("/api/parts/", json=SAMPLE_PART, headers=auth_headers)
    assert response.status_code == 400
    assert "already" in response.json()["detail"]


def test_get_all_parts(client, auth_headers):
    client.post("/api/parts/", json=SAMPLE_PART, headers=auth_headers)
    response = client.get("/api/parts/", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_search_by_name(client, auth_headers):
    client.post("/api/parts/", json=SAMPLE_PART, headers=auth_headers)
    response = client.get("/api/parts/?q=bremseklosser", headers=auth_headers)
    assert response.status_code == 200
    assert any("Bremseklosser" in p["name"] for p in response.json())


def test_search_by_part_number(client, auth_headers):
    client.post("/api/parts/", json=SAMPLE_PART, headers=auth_headers)
    response = client.get("/api/parts/?q=TEST-001", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_search_by_car(client, auth_headers):
    client.post("/api/parts/", json=SAMPLE_PART, headers=auth_headers)
    response = client.get("/api/parts/?car_make=Toyota&car_model=Corolla", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_update_part(client, auth_headers):
    create_resp = client.post("/api/parts/", json=SAMPLE_PART, headers=auth_headers)
    part_id = create_resp.json()["id"]
    response = client.put(
        f"/api/parts/{part_id}",
        json={"stock_quantity": 20, "unit_price": 999.0},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["stock_quantity"] == 20
    assert response.json()["unit_price"] == 999.0


def test_delete_part(client, auth_headers):
    create_resp = client.post("/api/parts/", json=SAMPLE_PART, headers=auth_headers)
    part_id = create_resp.json()["id"]
    del_resp = client.delete(f"/api/parts/{part_id}", headers=auth_headers)
    assert del_resp.status_code == 204
    get_resp = client.get(f"/api/parts/{part_id}", headers=auth_headers)
    assert get_resp.status_code == 404


def test_low_stock_filter(client, auth_headers):
    low_stock_part = {**SAMPLE_PART, "part_number": "LOW-001", "stock_quantity": 2, "low_stock_threshold": 5}
    client.post("/api/parts/", json=low_stock_part, headers=auth_headers)
    response = client.get("/api/parts/?low_stock_only=true", headers=auth_headers)
    assert response.status_code == 200
    assert all(p["stock_quantity"] <= p["low_stock_threshold"] for p in response.json())


def test_stock_status_values(client, auth_headers):
    # Empty stock
    empty_part = {**SAMPLE_PART, "part_number": "EMPTY-001", "stock_quantity": 0}
    r = client.post("/api/parts/", json=empty_part, headers=auth_headers)
    assert r.json()["stock_status"] == "Empty"

    # Low stock
    low_part = {**SAMPLE_PART, "part_number": "LOW-002", "stock_quantity": 3, "low_stock_threshold": 5}
    r = client.post("/api/parts/", json=low_part, headers=auth_headers)
    assert r.json()["stock_status"] == "Low"


def test_unauthorized_access(client):
    response = client.get("/api/parts/")
    assert response.status_code == 401


def test_import_template_downloads_xlsx(client, auth_headers):
    """The /import-template route must resolve before /{part_id} and return a
    real .xlsx (regression: it used to be swallowed by the part-id route)."""
    r = client.get("/api/parts/import-template", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert "spreadsheetml.sheet" in r.headers["content-type"]
    assert r.content[:2] == b"PK"  # xlsx is a zip; starts with PK


def test_bulk_delete_parts(client, auth_headers):
    a = client.post("/api/parts/", json={**SAMPLE_PART, "part_number": "BULK-1"}, headers=auth_headers).json()
    b = client.post("/api/parts/", json={**SAMPLE_PART, "part_number": "BULK-2"}, headers=auth_headers).json()
    r = client.post("/api/parts/bulk-delete", json={"ids": [a["id"], b["id"]]}, headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["deleted"] == 2
    assert client.get(f"/api/parts/{a['id']}", headers=auth_headers).status_code == 404


def test_bulk_delete_keeps_referenced_parts(client, auth_headers):
    p = client.post("/api/parts/", json={**SAMPLE_PART, "part_number": "BULK-REF"}, headers=auth_headers).json()
    client.post("/api/orders/", json={"customer_id": 1, "part_id": p["id"], "quantity": 1}, headers=auth_headers)
    r = client.post("/api/parts/bulk-delete", json={"ids": [p["id"]]}, headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["deleted"] == 0
    assert len(r.json()["blocked"]) == 1
    # Still there because an order references it
    assert client.get(f"/api/parts/{p['id']}", headers=auth_headers).status_code == 200
