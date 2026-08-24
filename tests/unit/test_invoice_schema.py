"""Validate the golden set's ground_truth against the invoice schema."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from docextract.schemas.invoice import ExtractionResult

ROOT = Path(__file__).resolve().parents[2]  # parents[2] = project root 
EXPECTED_DIR = ROOT / "golden_set" / "expected"

CORE_FIELDS = {
    "vendor_name", "vendor_address", "customer_name", "customer_address",
    "invoice_number", "invoice_date", "due_date", "currency",
    "line_items", "totals",
}


def _golden_files() -> list[Path]:
    return sorted(EXPECTED_DIR.glob("invoice_*.json"))


@pytest.mark.parametrize("path", _golden_files(), ids=lambda p: p.stem)
def test_ground_truth_validates_against_schema(path: Path) -> None:
    gt = json.loads(path.read_text(encoding="utf-8"))["ground_truth"]
    subset = {k: gt[k] for k in CORE_FIELDS}
    ExtractionResult(**subset) # construct ExtractionResult and let Pydantic coerce + reject bad data