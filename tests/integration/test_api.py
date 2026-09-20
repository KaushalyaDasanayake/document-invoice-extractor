from fastapi.testclient import TestClient

from docextract.api.deps import get_ocr_engine
from docextract.api.main import app
from docextract.ocr.engine import OcrResult


def fake_engine():
    # never touch tesseract returns instantly
    class FakeOCREngine:
        def __call__(self, *args, **kwds):
            return OcrResult(raw_text="fake text", num_pages=1)
    return FakeOCREngine()


# Override the dependency before the client starts
def test_extract_returns_text(monkeypatch):
    app.dependency_overrides[get_ocr_engine] = fake_engine
    client = TestClient(app)
    response = client.post("/v1/extract", files={"file": ("a.png", b"data", "image/png")})
    assert response.status_code == 200
    assert response.json()["raw_text"] == "fake text"
    app.dependency_overrides.clear() # clean up for other tests