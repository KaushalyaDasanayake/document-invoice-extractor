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


def test_extract_with_confidences_and_redact():
    app.dependency_overrides[get_ocr_engine] = lambda: lambda path: OcrResult(
        raw_text=SAMPLE_OCR, num_pages=1
    )

    # Without redact
    res = client.post(
        "/v1/extract",
        files={"file": ("invoice.pdf", b"dummy")},
        headers=HEADERS,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["invoice"]["customer_name"] == "Wayne Enterprises"
    assert "confidences" in data
    assert data["confidences"]["invoice_number"] >= 0.9

    # With redact=True
    res_redacted = client.post(
        "/v1/extract?redact=true",
        files={"file": ("invoice.pdf", b"dummy")},
        headers=HEADERS,
    )
    assert res_redacted.status_code == 200
    red_data = res_redacted.json()
    assert "Wayne Enterprises" not in red_data["invoice"]["customer_name"]
    assert red_data["invoice"]["customer_address"] == "[REDACTED ADDRESS]"


def test_export_csv_and_json():
    invoice_payload = {
        "vendor_name": "Acme Corp",
        "vendor_address": "123 Street",
        "customer_name": "Wayne Enterprises",
        "customer_address": "Gotham City",
        "invoice_number": "INV-2026-9000",
        "invoice_date": "2026-06-01",
        "due_date": "2026-06-30",
        "currency": "USD",
        "line_items": [
            {
                "description": "Widget A",
                "quantity": 2.0,
                "unit_price": 50.0,
                "line_total": 100.0,
            }
        ],
        "totals": {
            "subtotal": 100.0,
            "tax": 10.0,
            "shipping": 0.0,
            "grand_total": 110.0,
        },
    }

    # Test CSV export
    res_csv = client.post("/v1/export/csv", json=invoice_payload, headers=HEADERS)
    assert res_csv.status_code == 200
    assert res_csv.headers["content-type"].startswith("text/csv")
    csv_text = res_csv.text
    assert "Invoice Number,INV-2026-9000" in csv_text
    assert "Widget A,2.0,50.0,100.0" in csv_text
    assert "Grand Total,110.0" in csv_text

    # Test JSON export
    res_json = client.post("/v1/export/json", json=invoice_payload, headers=HEADERS)
    assert res_json.status_code == 200
    assert res_json.json()["invoice_number"] == "INV-2026-9000"
