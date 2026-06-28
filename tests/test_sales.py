"""Tests for the sales summary endpoint (delivered orders + paid credit sales)."""

PART = {"part_number": "SALE-1", "name": "Sold Part", "category": "Brakes", "unit_price": 100.0, "stock_quantity": 50}


def test_sales_counts_delivered_orders(client, auth_headers):
    part = client.post("/api/parts/", json=PART, headers=auth_headers).json()
    # A delivered order = a sale
    client.post("/api/orders/", json={"customer_id": 1, "part_id": part["id"], "quantity": 3, "status": "Delivered"}, headers=auth_headers)
    # A New order is NOT a sale yet
    client.post("/api/orders/", json={"customer_id": 1, "part_id": part["id"], "quantity": 5}, headers=auth_headers)

    s = client.get("/api/analytics/sales?period=all", headers=auth_headers).json()
    assert s["total_units"] == 3
    assert s["total_revenue"] == 300.0
    assert s["transactions"] == 1
    assert s["top_parts"][0]["part_number"] == "SALE-1"


def test_sales_includes_paid_credit_sales(client, auth_headers):
    part = client.post("/api/parts/", json={**PART, "part_number": "SALE-2"}, headers=auth_headers).json()
    cust = client.post("/api/customers/", json={"name": "Cred Cust"}, headers=auth_headers).json()
    loan = client.post("/api/loans/", json={
        "customer_id": cust["id"], "part_id": part["id"], "quantity": 2,
        "loan_price": 100.0, "employee_name": "Emp",
    }, headers=auth_headers).json()
    # Unpaid credit sale should NOT count yet
    assert client.get("/api/analytics/sales?period=all", headers=auth_headers).json()["total_units"] == 0
    # Mark paid → becomes a sale
    client.post(f"/api/loans/{loan['id']}/return", headers=auth_headers)
    s = client.get("/api/analytics/sales?period=all", headers=auth_headers).json()
    assert s["total_units"] == 2
    assert s["total_revenue"] == 200.0
