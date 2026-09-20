from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_DIR = ROOT / "golden_set"
EXPECTED_DIR = GOLDEN_DIR / "expected"
AGGREGATE_JSON = GOLDEN_DIR / "invoices_v1.json"
SESSIONS_JSON = GOLDEN_DIR / "sessions.json"

REQUIRED_TOP_LEVEL = {
    "sample_id",
    "template",
    "page_count",
    "source_files",
    "ground_truth",
    "bounding_boxes",
}

REQUIRED_GROUND_TRUTH = {
    "vendor_name",
    "vendor_address",
    "customer_name",
    "customer_address",
    "invoice_number",
    "invoice_date",
    "due_date",
    "currency",
    "line_items",
    "totals",
    "payment",
    "notes",
}

REQUIRED_TOTALS = {"subtotal", "tax", "shipping", "grand_total"}
REQUIRED_PAYMENT = {"bank_name", "account_name", "account_number"}
REQUIRED_BBOX_KEYS = {
    "invoice_number",
    "invoice_date",
    "due_date",
    "vendor_name",
    "customer_name",
    "line_items",
    "grand_total",
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def fail(message: str) -> None:
    raise ValueError(message)


def require_keys(obj: dict[str, Any], required: set[str], context: str) -> None:
    missing = sorted(required - obj.keys())
    if missing:
        fail(f"{context} is missing keys: {', '.join(missing)}")


def validate_bbox_entry(entry: dict[str, Any], context: str) -> None:
    require_keys(entry, {"page", "bbox"}, context)
    if not isinstance(entry["page"], int) or entry["page"] < 1:
        fail(f"{context}.page must be a positive integer")
    bbox = entry["bbox"]
    if not isinstance(bbox, list) or len(bbox) != 4 or not all(isinstance(v, int) for v in bbox):
        fail(f"{context}.bbox must be a list of 4 integers")


def validate_line_item(item: dict[str, Any], context: str) -> None:
    require_keys(item, {"description", "quantity", "unit_price", "line_total"}, context)
    if not isinstance(item["description"], str) or not item["description"].strip():
        fail(f"{context}.description must be a non-empty string")
    if not isinstance(item["quantity"], (int, float)):
        fail(f"{context}.quantity must be numeric")
    if not isinstance(item["unit_price"], (int, float)):
        fail(f"{context}.unit_price must be numeric")
    if not isinstance(item["line_total"], (int, float)):
        fail(f"{context}.line_total must be numeric")


def validate_record(record: dict[str, Any], expected_sample_id: str | None = None) -> None:
    require_keys(record, REQUIRED_TOP_LEVEL, "record")

    sample_id = record["sample_id"]
    if expected_sample_id and sample_id != expected_sample_id:
        fail(f"record sample_id {sample_id!r} does not match file name {expected_sample_id!r}")

    if not isinstance(record["page_count"], int) or record["page_count"] < 1:
        fail(f"{sample_id}: page_count must be a positive integer")

    source_files = record["source_files"]
    if not isinstance(source_files, dict):
        fail(f"{sample_id}: source_files must be an object")
    require_keys(source_files, {"html", "pdf", "png"}, f"{sample_id}.source_files")
    if not isinstance(source_files["png"], list) or len(source_files["png"]) != record["page_count"]:
        fail(f"{sample_id}: png source_files count must match page_count")

    ground_truth = record["ground_truth"]
    if not isinstance(ground_truth, dict):
        fail(f"{sample_id}: ground_truth must be an object")
    require_keys(ground_truth, REQUIRED_GROUND_TRUTH, f"{sample_id}.ground_truth")

    line_items = ground_truth["line_items"]
    if not isinstance(line_items, list) or not line_items:
        fail(f"{sample_id}: ground_truth.line_items must be a non-empty list")
    for idx, item in enumerate(line_items, start=1):
        if not isinstance(item, dict):
            fail(f"{sample_id}: line_items[{idx}] must be an object")
        validate_line_item(item, f"{sample_id}.line_items[{idx}]")

    totals = ground_truth["totals"]
    if not isinstance(totals, dict):
        fail(f"{sample_id}: totals must be an object")
    require_keys(totals, REQUIRED_TOTALS, f"{sample_id}.totals")

    payment = ground_truth["payment"]
    if not isinstance(payment, dict):
        fail(f"{sample_id}: payment must be an object")
    require_keys(payment, REQUIRED_PAYMENT, f"{sample_id}.payment")

    boxes = record["bounding_boxes"]
    if not isinstance(boxes, dict):
        fail(f"{sample_id}: bounding_boxes must be an object")
    require_keys(boxes, REQUIRED_BBOX_KEYS, f"{sample_id}.bounding_boxes")

    for key in ["invoice_number", "invoice_date", "due_date", "vendor_name", "customer_name", "grand_total"]:
        validate_bbox_entry(boxes[key], f"{sample_id}.bounding_boxes.{key}")

    if not isinstance(boxes["line_items"], list) or not boxes["line_items"]:
        fail(f"{sample_id}: bounding_boxes.line_items must be a non-empty list")
    for idx, entry in enumerate(boxes["line_items"], start=1):
        if not isinstance(entry, dict):
            fail(f"{sample_id}: bounding_boxes.line_items[{idx}] must be an object")
        require_keys(entry, {"description", "page", "bbox"}, f"{sample_id}.bounding_boxes.line_items[{idx}]")
        validate_bbox_entry(entry, f"{sample_id}.bounding_boxes.line_items[{idx}]")


def validate_expected_files() -> list[dict[str, Any]]:
    if not EXPECTED_DIR.exists():
        fail(f"missing directory: {EXPECTED_DIR}")

    records = []
    for path in sorted(EXPECTED_DIR.glob("*.json")):
        record = load_json(path)
        if not isinstance(record, dict):
            fail(f"{path.name} must contain a JSON object")
        validate_record(record, expected_sample_id=path.stem)
        records.append(record)
    if not records:
        fail("no per-sample JSON files found in golden_set/expected")
    return records


def validate_aggregate(expected_records: list[dict[str, Any]]) -> None:
    if not AGGREGATE_JSON.exists():
        fail(f"missing aggregate file: {AGGREGATE_JSON}")
    aggregate = load_json(AGGREGATE_JSON)
    if not isinstance(aggregate, list):
        fail("aggregate golden set must be a JSON list")

    if len(aggregate) != len(expected_records):
        fail("aggregate record count does not match per-sample JSON count")

    aggregate_ids = []
    for record in aggregate:
        if not isinstance(record, dict):
            fail("aggregate items must be JSON objects")
        validate_record(record)
        aggregate_ids.append(record["sample_id"])

    expected_ids = [record["sample_id"] for record in expected_records]
    if sorted(aggregate_ids) != sorted(expected_ids):
        fail("aggregate sample IDs do not match per-sample JSON files")


def validate_sessions(expected_records: list[dict[str, Any]]) -> None:
    if not SESSIONS_JSON.exists():
        fail(f"missing sessions manifest: {SESSIONS_JSON}")
    sessions = load_json(SESSIONS_JSON)
    if not isinstance(sessions, list):
        fail("sessions manifest must be a JSON list")

    expected_ids = {record["sample_id"] for record in expected_records}
    session_ids = set()
    for session in sessions:
        if not isinstance(session, dict):
            fail("session entries must be JSON objects")
        require_keys(session, {"session_id", "input", "expected_output", "summary"}, "session")
        session_id = session["session_id"]
        if session_id in session_ids:
            fail(f"duplicate session ID: {session_id}")
        if session_id not in expected_ids:
            fail(f"session references unknown sample: {session_id}")
        if not isinstance(session["input"], dict) or not session["input"].get("pdf"):
            fail(f"{session_id}.input must include a PDF path")
        if session["expected_output"] != f"expected/{session_id}.json":
            fail(f"{session_id}.expected_output points to the wrong file")
        if not isinstance(session["summary"], str) or not session["summary"].strip():
            fail(f"{session_id}.summary must be a non-empty string")
        session_ids.add(session_id)

    if session_ids != expected_ids:
        fail("sessions manifest IDs do not match per-sample JSON files")


def main() -> int:
    try:
        expected_records = validate_expected_files()
        validate_aggregate(expected_records)
        validate_sessions(expected_records)
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"Golden set validation failed: {exc}", file=sys.stderr)
        return 1

    print(f"Golden set validation passed for {len(expected_records)} samples.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
