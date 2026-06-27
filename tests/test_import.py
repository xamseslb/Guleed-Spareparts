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


def test_import_missing_required_column(client, auth_headers):
    r = client.post("/api/parts/import", files=_csv("part_number,name\nX-1,Foo\n"), headers=auth_headers)
    assert r.status_code == 400
    assert "category" in r.json()["detail"].lower() or "price" in r.json()["detail"].lower()


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
