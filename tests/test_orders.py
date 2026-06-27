"""
Tests for the orders API: price snapshotting and stock synchronization.
"""

PART = {
    "part_number": "ORD-001",
    "name": "Test Alternator",
    "category": "Electrical",
    "stock_quantity": 10,
    "low_stock_threshold": 2,
    "unit_price": 1500.0,
}


def _create_part(client, auth_headers, **overrides):
    payload = {**PART, **overrides}
    r = client.post("/api/parts/", json=payload, headers=auth_headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_create_order_snapshots_part_price(client, auth_headers):
    part = _create_part(client, auth_headers)
    r = client.post(
        "/api/orders/",
        json={"customer_id": 1, "part_id": part["id"], "quantity": 2},
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    data = r.json()
    # Price was taken from the part, total computed
    assert data["unit_price_at_order"] == 1500.0
    assert data["unit_price"] == 1500.0
    assert data["total_price"] == 3000.0
    assert data["status"] == "New"


def test_create_order_with_explicit_price(client, auth_headers):
    part = _create_part(client, auth_headers, part_number="ORD-002")
    r = client.post(
        "/api/orders/",
        json={"customer_id": 1, "part_id": part["id"], "quantity": 1, "unit_price_at_order": 999.0},
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    assert r.json()["unit_price_at_order"] == 999.0


def test_new_order_does_not_touch_stock(client, auth_headers):
    part = _create_part(client, auth_headers, part_number="ORD-003")
    client.post(
        "/api/orders/",
        json={"customer_id": 1, "part_id": part["id"], "quantity": 3},
        headers=auth_headers,
    )
    after = client.get(f"/api/parts/{part['id']}", headers=auth_headers).json()
    assert after["stock_quantity"] == 10  # unchanged while "New"


def test_delivered_order_decrements_stock(client, auth_headers):
    part = _create_part(client, auth_headers, part_number="ORD-004")
    client.post(
        "/api/orders/",
        json={"customer_id": 1, "part_id": part["id"], "quantity": 4, "status": "Delivered"},
        headers=auth_headers,
    )
    after = client.get(f"/api/parts/{part['id']}", headers=auth_headers).json()
    assert after["stock_quantity"] == 6  # 10 - 4


def test_delivering_via_update_then_reverting_restores_stock(client, auth_headers):
    part = _create_part(client, auth_headers, part_number="ORD-005")
    order = client.post(
        "/api/orders/",
        json={"customer_id": 1, "part_id": part["id"], "quantity": 5},
        headers=auth_headers,
    ).json()

    # Deliver → stock drops
    client.put(f"/api/orders/{order['id']}", json={"status": "Delivered"}, headers=auth_headers)
    assert client.get(f"/api/parts/{part['id']}", headers=auth_headers).json()["stock_quantity"] == 5

    # Revert to Processing → stock restored
    client.put(f"/api/orders/{order['id']}", json={"status": "Processing"}, headers=auth_headers)
    assert client.get(f"/api/parts/{part['id']}", headers=auth_headers).json()["stock_quantity"] == 10


def test_delivered_order_rejected_when_insufficient_stock(client, auth_headers):
    part = _create_part(client, auth_headers, part_number="ORD-006", stock_quantity=3)
    r = client.post(
        "/api/orders/",
        json={"customer_id": 1, "part_id": part["id"], "quantity": 5, "status": "Delivered"},
        headers=auth_headers,
    )
    assert r.status_code == 400
    assert "Not enough stock" in r.json()["detail"]
    # Stock untouched after a rejected delivery
    assert client.get(f"/api/parts/{part['id']}", headers=auth_headers).json()["stock_quantity"] == 3


def test_delete_delivered_order_restores_stock(client, auth_headers):
    part = _create_part(client, auth_headers, part_number="ORD-007")
    order = client.post(
        "/api/orders/",
        json={"customer_id": 1, "part_id": part["id"], "quantity": 4, "status": "Delivered"},
        headers=auth_headers,
    ).json()
    assert client.get(f"/api/parts/{part['id']}", headers=auth_headers).json()["stock_quantity"] == 6

    client.delete(f"/api/orders/{order['id']}", headers=auth_headers)
    assert client.get(f"/api/parts/{part['id']}", headers=auth_headers).json()["stock_quantity"] == 10


def test_cannot_delete_customer_with_linked_order(client, auth_headers):
    cust = client.post("/api/customers/", json={"name": "Linked Customer"}, headers=auth_headers).json()
    part = _create_part(client, auth_headers, part_number="ORD-DEL1")
    client.post(
        "/api/orders/",
        json={"customer_id": cust["id"], "part_id": part["id"], "quantity": 1},
        headers=auth_headers,
    )
    r = client.delete(f"/api/customers/{cust['id']}", headers=auth_headers)
    assert r.status_code == 400
    assert "Cannot delete customer" in r.json()["detail"]


def test_cannot_delete_part_with_linked_order(client, auth_headers):
    part = _create_part(client, auth_headers, part_number="ORD-DEL2")
    client.post(
        "/api/orders/",
        json={"customer_id": 1, "part_id": part["id"], "quantity": 1},
        headers=auth_headers,
    )
    r = client.delete(f"/api/parts/{part['id']}", headers=auth_headers)
    assert r.status_code == 400
    assert "Cannot delete part" in r.json()["detail"]


def test_order_stores_group_ref(client, auth_headers):
    part = _create_part(client, auth_headers, part_number="GRP-1")
    r = client.post(
        "/api/orders/",
        json={"customer_id": 1, "part_id": part["id"], "quantity": 1, "group_ref": "G-abc123"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    assert r.json()["group_ref"] == "G-abc123"


def test_order_without_a_customer(client, auth_headers):
    part = _create_part(client, auth_headers, part_number="WALK-1")
    r = client.post("/api/orders/", json={"part_id": part["id"], "quantity": 1}, headers=auth_headers)
    assert r.status_code == 201, r.text
    assert r.json()["customer_id"] is None
    assert r.json()["customer_name"] is None


def test_order_with_typed_customer_name(client, auth_headers):
    part = _create_part(client, auth_headers, part_number="WALK-2")
    r = client.post(
        "/api/orders/",
        json={"part_id": part["id"], "quantity": 1, "customer_name": "Walk-in Bob"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    assert r.json()["customer_id"] is None
    assert r.json()["customer_name"] == "Walk-in Bob"


def test_can_update_order_price(client, auth_headers):
    part = _create_part(client, auth_headers, part_number="PRICE-1")
    order = client.post(
        "/api/orders/",
        json={"customer_id": 1, "part_id": part["id"], "quantity": 2},
        headers=auth_headers,
    ).json()
    r = client.put(f"/api/orders/{order['id']}", json={"unit_price_at_order": 555.0}, headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["unit_price_at_order"] == 555.0
    assert r.json()["total_price"] == 1110.0  # 555 * 2


def test_create_order_unknown_part_returns_404(client, auth_headers):
    r = client.post(
        "/api/orders/",
        json={"customer_id": 1, "part_id": 9999, "quantity": 1},
        headers=auth_headers,
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "Part not found"
