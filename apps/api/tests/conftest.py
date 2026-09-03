import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
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
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
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
def disable_external_integrations(monkeypatch):
    """Tests never call external WhatsApp services unless they opt in."""
    monkeypatch.setattr(settings, "whatsapp_group_creation_enabled", False)
    monkeypatch.setattr(settings, "whatsapp_bridge_base_url", "")

    monkeypatch.setattr(settings, "whatsapp_cloud_enabled", False)
    monkeypatch.setattr(settings, "whatsapp_cloud_verify_token", "")
    monkeypatch.setattr(settings, "whatsapp_cloud_app_secret", "")
    monkeypatch.setattr(settings, "whatsapp_cloud_access_token", "")
    monkeypatch.setattr(settings, "whatsapp_cloud_phone_number_id", "")
    monkeypatch.setattr(settings, "whatsapp_cloud_auto_start_enabled", False)
    monkeypatch.setattr(
        settings,
        "whatsapp_cloud_onboarding_template_name",
        "",
    )
