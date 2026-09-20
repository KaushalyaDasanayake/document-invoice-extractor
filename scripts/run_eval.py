"""Compare predicted invoice JSON files with the frozen golden set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_DIR = ROOT / "golden_set"
EXPECTED_DIR = GOLDEN_DIR / "expected"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def fields(record: dict[str, Any]) -> dict[str, Any]:
    """Return comparable field names without comparing bounding boxes."""
    source = record.get("ground_truth", record)
    result: dict[str, Any] = {}
    for key, value in source.items():
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                result[f"{key}.{child_key}"] = child_value
        else:
            result[key] = value
    return result


def evaluate(predictions_dir: Path) -> dict[str, Any]:
    predictions_dir = predictions_dir.resolve()
    totals = {"true_positive": 0, "false_positive": 0, "false_negative": 0}
    per_field: dict[str, dict[str, int]] = {}
    samples = []

    for expected_path in sorted(EXPECTED_DIR.glob("*.json")):
        sample_id = expected_path.stem
        prediction_path = predictions_dir / expected_path.name
        expected = fields(load_json(expected_path))
        predicted = fields(load_json(prediction_path)) if prediction_path.exists() else {}
        sample_matches = 0

        for field_name, expected_value in expected.items():
            stats = per_field.setdefault(field_name, {"true_positive": 0, "false_positive": 0, "false_negative": 0})
            predicted_value = predicted.get(field_name)
            if predicted_value == expected_value:
                totals["true_positive"] += 1
                stats["true_positive"] += 1
                sample_matches += 1
            else:
                totals["false_negative"] += 1
                stats["false_negative"] += 1
                if field_name in predicted:
                    totals["false_positive"] += 1
                    stats["false_positive"] += 1

        samples.append({
            "sample_id": sample_id,
            "matched_fields": sample_matches,
            "total_fields": len(expected),
            "prediction_file": str(prediction_path.relative_to(ROOT)) if prediction_path.exists() else None,
        })

    precision_denominator = totals["true_positive"] + totals["false_positive"]
    recall_denominator = totals["true_positive"] + totals["false_negative"]
    return {
        "schema_version": "v1",
        "totals": totals,
        "precision": totals["true_positive"] / precision_denominator if precision_denominator else 0.0,
        "recall": totals["true_positive"] / recall_denominator if recall_denominator else 0.0,
        "per_field": per_field,
        "samples": samples,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "eval" / "metrics.json")
    args = parser.parse_args()

    metrics = evaluate(args.predictions_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(f"Evaluated {len(metrics['samples'])} samples")
    print(f"Precision: {metrics['precision']:.3f}; Recall: {metrics['recall']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
