from fastapi.testclient import TestClient

from docextract.api.deps import get_ocr_engine
from docextract.api.main import app
from docextract.ocr.engine import OcrResult

client = TestClient(app)

SAMPLE_OCR = """
Acme Industrial Supply
123 Factory Lane, Detroit MI
Invoice #: INV-2026-9000
Date: 2026-06-01
Due Date: 2026-06-30
Bill To:
Wayne Enterprises
1007 Mountain Drive, Gotham
Widget A 2 USD 50.00 USD 100.00
Subtotal USD 100.00
Tax USD 10.00
Grand Total USD 110.00
"""

HEADERS = {"X-API-Key": "dev-key-change-in-prod"}


def test_ui_served():
    res = client.get("/")
    assert res.status_code == 200
    assert "Invoice Extractor Studio" in res.text


def test_async_job_lifecycle():
    app.dependency_overrides[get_ocr_engine] = lambda: lambda path: OcrResult(
        raw_text=SAMPLE_OCR, num_pages=1
    )

    # 1. Submit job
    res = client.post(
        "/v1/jobs",
        files={"file": ("invoice.pdf", b"dummy content")},
        headers=HEADERS,
    )
    assert res.status_code == 200
    data = res.json()
    assert "job_id" in data
    job_id = data["job_id"]

    # 2. Poll job status
    # In TestClient, background tasks run synchronously during the request
    poll_res = client.get(f"/v1/jobs/{job_id}", headers=HEADERS)
    assert poll_res.status_code == 200
    job_info = poll_res.json()
    assert job_info["job_id"] == job_id
    assert job_info["status"] in {"completed", "pending"}
    if job_info["status"] == "completed":
        assert job_info["result"]["invoice"]["invoice_number"] == "INV-2026-9000"


def test_job_not_found():
    res = client.get("/v1/jobs/non_existent_job", headers=HEADERS)
    assert res.status_code == 404
