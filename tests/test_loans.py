"""
Tests for the loans (credit-sale) flow: a part taken on credit is reserved
while unpaid, and removed from stock once paid (never restored).
"""

PART = {
    "part_number": "LN-1",
    "name": "Credit Part",
    "category": "Misc",
    "stock_quantity": 10,
    "unit_price": 100.0,
}


def _part(client, h, **overrides):
    return client.post("/api/parts/", json={**PART, **overrides}, headers=h).json()


def _customer(client, h):
    return client.post("/api/customers/", json={"name": "Credit Customer"}, headers=h).json()


def _loan(client, h, part_id, customer_id, quantity=3):
    return client.post(
        "/api/loans/",
        json={"customer_id": customer_id, "part_id": part_id, "quantity": quantity,
              "loan_price": 100, "employee_name": "Hamse"},
        headers=h,
    )


def test_credit_sale_reserves_while_unpaid(client, auth_headers):
    part = _part(client, auth_headers)
    cust = _customer(client, auth_headers)
    r = _loan(client, auth_headers, part["id"], cust["id"], 3)
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "unpaid"

    p = client.get(f"/api/parts/{part['id']}", headers=auth_headers).json()
    assert p["stock_quantity"] == 10          # still physically counted
    assert p["available_quantity"] == 7       # 10 - 3 reserved


def test_marking_paid_removes_stock_and_does_not_restore(client, auth_headers):
    part = _part(client, auth_headers, part_number="LN-2")
    cust = _customer(client, auth_headers)
    loan = _loan(client, auth_headers, part["id"], cust["id"], 3).json()

    client.post(f"/api/loans/{loan['id']}/return", headers=auth_headers)

    p = client.get(f"/api/parts/{part['id']}", headers=auth_headers).json()
    assert p["stock_quantity"] == 7           # sold → removed from stock
    assert p["available_quantity"] == 7       # NOT restored to 10


def test_cannot_pay_twice(client, auth_headers):
    part = _part(client, auth_headers, part_number="LN-3")
    cust = _customer(client, auth_headers)
    loan = _loan(client, auth_headers, part["id"], cust["id"], 1).json()
    client.post(f"/api/loans/{loan['id']}/return", headers=auth_headers)
    r = client.post(f"/api/loans/{loan['id']}/return", headers=auth_headers)
    assert r.status_code == 400
    assert "already" in r.json()["detail"].lower()


def test_deleting_unpaid_releases_reserved_stock(client, auth_headers):
    part = _part(client, auth_headers, part_number="LN-4")
    cust = _customer(client, auth_headers)
    loan = _loan(client, auth_headers, part["id"], cust["id"], 4).json()
    assert client.get(f"/api/parts/{part['id']}", headers=auth_headers).json()["available_quantity"] == 6

    client.delete(f"/api/loans/{loan['id']}", headers=auth_headers)
    p = client.get(f"/api/parts/{part['id']}", headers=auth_headers).json()
    assert p["available_quantity"] == 10      # reservation released
    assert p["stock_quantity"] == 10


def test_delete_unpaid_loan_releases_reservation(client, auth_headers):
    part = _part(client, auth_headers, part_number="LN-DEL1")
    cust = _customer(client, auth_headers)
    loan = _loan(client, auth_headers, part["id"], cust["id"], 3).json()
    # While unpaid: reserved (loaned 3), stock still 10, available 7
    p = client.get(f"/api/parts/{part['id']}", headers=auth_headers).json()
    assert p["loaned_quantity"] == 3 and p["available_quantity"] == 7

    assert client.delete(f"/api/loans/{loan['id']}", headers=auth_headers).status_code == 204
    p = client.get(f"/api/parts/{part['id']}", headers=auth_headers).json()
    assert p["loaned_quantity"] == 0          # reservation released
    assert p["stock_quantity"] == 10
    assert p["available_quantity"] == 10       # back to normal


def test_delete_paid_loan_restores_stock(client, auth_headers):
    part = _part(client, auth_headers, part_number="LN-DEL2")
    cust = _customer(client, auth_headers)
    loan = _loan(client, auth_headers, part["id"], cust["id"], 3).json()
    # Mark paid → sold → stock 7, loaned 0
    client.post(f"/api/loans/{loan['id']}/return", headers=auth_headers)
    p = client.get(f"/api/parts/{part['id']}", headers=auth_headers).json()
    assert p["stock_quantity"] == 7 and p["loaned_quantity"] == 0

    assert client.delete(f"/api/loans/{loan['id']}", headers=auth_headers).status_code == 204
    p = client.get(f"/api/parts/{part['id']}", headers=auth_headers).json()
    assert p["stock_quantity"] == 10           # sale undone, items back in stock


def test_cancel_unpaid_loan_releases_reservation(client, auth_headers):
    part = _part(client, auth_headers, part_number="LN-CAN1")
    cust = _customer(client, auth_headers)
    loan = _loan(client, auth_headers, part["id"], cust["id"], 3).json()
    r = client.post(f"/api/loans/{loan['id']}/cancel", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "cancelled"
    p = client.get(f"/api/parts/{part['id']}", headers=auth_headers).json()
    assert p["loaned_quantity"] == 0        # reservation released
    assert p["stock_quantity"] == 10        # never sold, stock untouched


def test_cannot_cancel_a_paid_loan(client, auth_headers):
    part = _part(client, auth_headers, part_number="LN-CAN2")
    cust = _customer(client, auth_headers)
    loan = _loan(client, auth_headers, part["id"], cust["id"], 2).json()
    client.post(f"/api/loans/{loan['id']}/return", headers=auth_headers)   # pay it
    r = client.post(f"/api/loans/{loan['id']}/cancel", headers=auth_headers)
    assert r.status_code == 400


def test_cannot_pay_a_cancelled_loan(client, auth_headers):
    part = _part(client, auth_headers, part_number="LN-CAN3")
    cust = _customer(client, auth_headers)
    loan = _loan(client, auth_headers, part["id"], cust["id"], 2).json()
    client.post(f"/api/loans/{loan['id']}/cancel", headers=auth_headers)
    r = client.post(f"/api/loans/{loan['id']}/return", headers=auth_headers)
    assert r.status_code == 400
