import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_db
from app.main import app


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_whatsapp_group_creation(monkeypatch):
    """Family creation calls out to the real WhatsApp bridge over HTTP.
    Tests must never depend on a live external service — default to a
    deterministic fake success; individual tests can monkeypatch this again
    to exercise the failure path.
    """

    def fake_create_whatsapp_group(subject: str, member_phones_e164: list[str]) -> str:
        return "123456789012345678@g.us"

    monkeypatch.setattr(
        "app.services.family_service.create_whatsapp_group", fake_create_whatsapp_group
    )
