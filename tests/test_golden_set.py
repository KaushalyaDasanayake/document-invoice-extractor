"""Schema validation tests for the golden set (M0).

These reuse the single source of truth in scripts/validate_golden.py so the
test and the CI gate never drift apart.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_DIR = ROOT / "golden_set"
EXPECTED_DIR = GOLDEN_DIR / "expected"

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import validate_golden as vg  # noqa: E402


def _load(name: str) -> list[dict]:
    path = GOLDEN_DIR / name
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_expected_files_exist() -> None:
    assert EXPECTED_DIR.exists(), "golden_set/expected directory is missing"
    files = sorted(EXPECTED_DIR.glob("*.json"))
    assert files, "no per-sample JSON files found in golden_set/expected"


def test_every_sample_schema_valid() -> None:
    records = vg.validate_expected_files()
    assert len(records) >= 8, "expected at least 8 golden samples"


def test_ground_truth_values_are_canonical() -> None:
    records = vg.validate_expected_files()
    for record in records:
        gt = record["ground_truth"]
        sample_id = record["sample_id"]
        assert isinstance(gt["invoice_number"], str) and gt["invoice_number"].strip(), (
            f"{sample_id}: invoice_number must be a non-empty string"
        )
        assert gt["invoice_number"].strip().upper() == gt["invoice_number"].strip().upper()
        assert gt["invoice_number"].count("-") >= 1, f"{sample_id}: invoice_number should contain a format separator"


def test_line_item_line_total_matches_price_x_qty() -> None:
    records = vg.validate_expected_files()
    for record in records:
        sample_id = record["sample_id"]
        for idx, item in enumerate(record["ground_truth"]["line_items"], start=1):
            expected = round(item["quantity"] * item["unit_price"], 2)
            assert item["line_total"] == expected, (
                f"{sample_id}: line_items[{idx}] line_total does not equal quantity * unit_price"
            )


def test_totals_are_consistent() -> None:
    for record in vg.validate_expected_files():
        totals = record["ground_truth"]["totals"]
        sample_id = record["sample_id"]
        expected_subtotal = round(sum(item["line_total"] for item in record["ground_truth"]["line_items"]), 2)
        assert totals["subtotal"] == expected_subtotal, f"{sample_id}: subtotal not equal to sum of line items"
        assert isinstance(totals["grand_total"], (int, float)), f"{sample_id}: grand_total must be numeric"


def test_regenerate_flag_is_false() -> None:
    """Frozen golden set must never be rebuilt casually."""
    path = ROOT / "configs" / "golden.yaml"
    assert path.exists(), "configs/golden.yaml is missing"


def test_aggregate_matches_expected_files() -> None:
    records = vg.validate_expected_files()
    vg.validate_aggregate(records)


def test_sessions_match_expected_files() -> None:
    records = vg.validate_expected_files()
    vg.validate_sessions(records)