"""Real end-to-end OCR test.

This test uploads a REAL golden-set PDF and runs REAL Tesseract, unlike
`test_api.py` which injects a fake engine. It is marked `slow` because it
is slow and CI-dependent (needs the tesseract binary), so CI skips it and run it on demand (`pytest -m slow`).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fastapi.testclient import TestClient

from docextract.api.main import app
from docextract.config import PROJECT_ROOT

client = TestClient(app)

# The golden-set sample to OCR with the real engine
SAMPLE = PROJECT_ROOT / "golden_set" / "inputs" / "invoice_001.pdf"


@pytest.mark.slow
@pytest.mark.skipif(not SAMPLE.exists(), reason="golden sample invoice_001.pdf not present")
def test_extract_real_pdf_returns_text() -> None:
    """Upload a real golden PDF and assert real OCR text comes back."""
    with SAMPLE.open("rb") as fh:
        response = client.post(
            "/v1/extract",
            files={"file": (SAMPLE.name, fh, "application/pdf")},
        )

    assert response.status_code == 200
    body = response.json()

    # A real PDF must have at least one page and non-empty text
    assert body["num_pages"] >= 1
    assert body["raw_text"].strip(), "OCR returned empty text for a real PDF"