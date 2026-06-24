"""
Konfigurasjon for pytest – delt test-database og test-klient.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base, get_db
from backend.main import app
from backend.services.auth_service import hash_password
from backend.models.user import User, UserRole

# Bruk in-memory SQLite for tester
TEST_DATABASE_URL = "sqlite:///./test_guleed.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    """Opprett og tøm database mellom hver test."""
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()

    # Opprett test-admin
    admin = User(
        username="testadmin",
        full_name="Test Admin",
        hashed_password=hash_password("testpass"),
        role=UserRole.ADMIN,
    )
    db.add(admin)
    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Returnerer JWT auth-headers for testadmin."""
    response = client.post(
        "/api/auth/login",
        data={"username": "testadmin", "password": "testpass"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
