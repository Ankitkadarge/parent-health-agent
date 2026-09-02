from sqlalchemy.exc import OperationalError


def test_root_describes_service(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "service": "Parent Health Agent API",
        "status": "ok",
        "health": "/health",
        "readiness": "/ready",
        "docs": "/docs",
    }
    assert response.headers["x-request-id"]


def test_health_is_process_only(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_checks_database(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}


def test_readiness_returns_503_when_database_fails(client, db_session, monkeypatch):
    def fail_execute(_statement):
        raise OperationalError(
            "SELECT 1",
            {},
            Exception("database unavailable"),
        )

    monkeypatch.setattr(db_session, "execute", fail_execute)
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {
        "detail": "Database is temporarily unavailable."
    }
