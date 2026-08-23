"""Integration tests for the /health and /ready liveness endpoints."""

from fastapi.testclient import TestClient

from docextract.api.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_returns_ready() -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_ready_503_when_engine_unavailable(monkeypatch) -> None:
    from docextract.api.deps import get_ocr_engine

    def broken_engine():
        return None

    app.dependency_overrides[get_ocr_engine] = broken_engine
    try:
        response = client.get("/ready")
        assert response.status_code == 503
        assert response.json() == {"detail": "OCR not ready: engine unavailable"}
    finally:
        app.dependency_overrides.clear()