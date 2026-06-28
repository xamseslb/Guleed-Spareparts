"""
Tests for bulk part import from CSV.
"""


def _csv(text):
    return {"file": ("parts.csv", text, "text/csv")}


def test_import_creates_parts(client, auth_headers):
    text = (
        "part_number,name,category,unit_price,stock_quantity\n"
        "IMP-1,Imported Brake,Brakes,100,5\n"
        "IMP-2,Imported Oil,Oil,50,3\n"
    )
    r = client.post("/api/parts/import", files=_csv(text), headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["created"] == 2
    parts = client.get("/api/parts/?q=IMP-1", headers=auth_headers).json()
    assert any(p["part_number"] == "IMP-1" and p["stock_quantity"] == 5 for p in parts)


def test_import_skips_duplicates(client, auth_headers):
    client.post("/api/parts/import", files=_csv("part_number,name,category,unit_price\nDUP-1,A,Brakes,10\n"), headers=auth_headers)
    text = "part_number,name,category,unit_price\nDUP-1,A,Brakes,10\nNEW-1,B,Oil,20\n"
    r = client.post("/api/parts/import", files=_csv(text), headers=auth_headers)
    d = r.json()
    assert d["created"] == 1
    assert d["skipped_duplicates"] == 1


def test_import_reports_row_errors(client, auth_headers):
    text = "part_number,name,category,unit_price\n,Missing PN,Brakes,10\nOK-1,Good,Oil,20\n"
    r = client.post("/api/parts/import", files=_csv(text), headers=auth_headers)
    d = r.json()
    assert d["created"] == 1
    assert d["error_count"] == 1


def test_import_requires_part_number_column(client, auth_headers):
    # Only the part number column is mandatory; without it the import is rejected.
    r = client.post("/api/parts/import", files=_csv("name,category\nFoo,Brakes\n"), headers=auth_headers)
    assert r.status_code == 400
    assert "part number" in r.json()["detail"].lower()


def test_import_with_only_part_number_and_stock(client, auth_headers):
    # The real-world case: a sheet with just part numbers and stock counts.
    text = "part_number,stock_quantity\nBARE-1,62\nBARE-2,48\n"
    r = client.post("/api/parts/import", files=_csv(text), headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["created"] == 2
    p = next(x for x in client.get("/api/parts/?q=BARE-1", headers=auth_headers).json() if x["part_number"] == "BARE-1")
    assert p["name"] == "BARE-1"            # name falls back to the part number
    assert p["category"] == "Uncategorized"  # blank category gets a placeholder
    assert p["unit_price"] == 0              # unknown price for now
    assert p["stock_quantity"] == 62


def test_import_blank_price_is_zero_not_nan(client, auth_headers):
    # A blank price cell must become 0 – a NaN serialises to null and crashes
    # the parts table (and breaks the stock-value total).
    text = "part_number,name,stock_quantity\nNAN-1,Some part,7\n"
    r = client.post("/api/parts/import", files=_csv(text), headers=auth_headers)
    assert r.status_code == 200, r.text
    parts = client.get("/api/parts/?q=NAN-1", headers=auth_headers).json()
    p = next(x for x in parts if x["part_number"] == "NAN-1")
    assert p["unit_price"] == 0           # real number, never null/NaN
    # The summary endpoint must still return a numeric stock value.
    summary = client.get("/api/analytics/summary", headers=auth_headers).json()
    assert isinstance(summary["total_stock_value_nok"], (int, float))


def test_import_template_downloads(client, auth_headers):
    # Regression: the static /import-template route must win over /{part_id}.
    r = client.get("/api/parts/import-template", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert "spreadsheetml" in r.headers["content-type"]
    assert len(r.content) > 0


def test_import_accepts_norwegian_headers(client, auth_headers):
    text = "varenummer,navn,kategori,pris\nNO-1,Norsk del,Bremser,123\n"
    r = client.post("/api/parts/import", files=_csv(text), headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["created"] == 1


def test_import_requires_admin(client, auth_headers):
    client.post("/api/auth/register", json={"username": "imp_emp", "full_name": "E", "password": "passord123", "role": "ansatt"}, headers=auth_headers)
    tok = client.post("/api/auth/login", data={"username": "imp_emp", "password": "passord123"}).json()["access_token"]
    r = client.post("/api/parts/import", files=_csv("part_number,name,category,unit_price\nA-1,A,Brakes,1\n"), headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403
