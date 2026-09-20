"""Application configuration loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "base.yaml"
# REQUIRED_OCR_KEYS = {"lang", "psm", "dpi", "tesseract_cmd"}


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)

# def load_config(path: str | Path | None = None) -> dict[str, Any]:
#     """Load and validate the application YAML configuration."""
#     config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
#     if not config_path.is_absolute():
#         config_path = PROJECT_ROOT / config_path

#     with config_path.open("r", encoding="utf-8") as handle:
#         config = yaml.safe_load(handle) or {}

#     if not isinstance(config, dict):
#         raise ValueError(f"Configuration must be a YAML mapping: {config_path}")

#     ocr = config.get("ocr")
#     if not isinstance(ocr, dict):
#         raise ValueError("Configuration must contain an 'ocr' mapping")

#     missing = REQUIRED_OCR_KEYS - ocr.keys()
#     if missing:
#         missing_keys = ", ".join(sorted(missing))
#         raise ValueError(f"Configuration is missing OCR keys: {missing_keys}")

#     return config
