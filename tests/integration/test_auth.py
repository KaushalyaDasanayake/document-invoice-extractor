from fastapi.testclient import TestClient

import docextract.api.auth as auth
from docextract.api.deps import get_ocr_engine
from docextract.api.main import app
from docextract.ocr.engine import OcrResult


def _fake_engine():
    """Return an OCR engine that never touches tesseract."""
    return lambda path: OcrResult(raw_text="fake text", num_pages=1)


def _make_client(app):
    return TestClient(app)


def test_extract_requires_key_when_configured(monkeypatch):
    # simulate the env var being set
    monkeypatch.setenv("DOCEXTRACT_API_KEY", "secret-key")
    # re-import so the module picks up the new env var
    monkeypatch.setattr(auth, "_API_KEY", "secret-key")

    app.dependency_overrides[get_ocr_engine] = _fake_engine
    client = _make_client(app)
    try:
        # without key -> 401
        r = client.post("/v1/extract", files={"file": ("a.png", b"data", "image/png")})
        assert r.status_code == 401
        # with key -> auth passes, request proceeds past 401
        r = client.post(
            "/v1/extract",
            files={"file": ("a.png", b"data", "image/png")},
            headers={"X-API-Key": "secret-key"},
        )
        assert r.status_code != 401
    finally:
        app.dependency_overrides.clear()