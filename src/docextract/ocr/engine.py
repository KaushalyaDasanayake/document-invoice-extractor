from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytesseract
from PIL import Image

SUPPORTED_IMAGES = {".png", ".jpg", ".jpeg"}
SUPPORTED_FILES = SUPPORTED_IMAGES | {".pdf"}

@dataclass(frozen=True)
class OcrResult:
    """Contains the complete OCR text and the number of processed pages."""

    raw_text: str
    num_pages: int


def _validate_config(config: dict[str, Any]) -> dict[str, Any]:
    """Reject unknown or invalid OCR settings before starting extraction."""
    if set(config) != {"ocr"}:
        raise ValueError("OCR config must contain only the 'ocr' section")

    ocr = config["ocr"]
    if not isinstance(ocr, dict): # Make sure it's a dictionary
        raise ValueError("The 'ocr' config must be a mapping") 

    required = {"lang", "psm", "dpi", "tesseract_cmd"}
    if set(ocr) != required:
        raise ValueError( 
            f"OCR config must contain exactly: {', '.join(sorted(required))}"
        )

    if not isinstance(ocr["lang"], str) or not ocr["lang"].strip():
        raise ValueError("ocr.lang must be a non-empty string")

    if not isinstance(ocr["psm"], int) or not 0 <= ocr["psm"] <= 13:
        raise ValueError("ocr.psm must be an integer from 0 to 13")

    if not isinstance(ocr["dpi"], int) or ocr["dpi"] <= 0:
        raise ValueError("ocr.dpi must be a positive integer")

    if not isinstance(ocr["tesseract_cmd"], str) or not ocr["tesseract_cmd"].strip():
        raise ValueError("ocr.tesseract_cmd must be a non-empty string")

    return ocr


def _ocr_image(image: Image.Image, ocr_config: dict[str, Any]) -> str:
    """Run Tesseract with the configured language and page segmentation mode."""
    pytesseract.pytesseract.tesseract_cmd = ocr_config["tesseract_cmd"]

    text = pytesseract.image_to_string( # sends an image to Tesseract OCR and gets the recognized text back.
        image,
        lang=ocr_config["lang"],
        config=f"--psm {ocr_config['psm']}"
    )

    if not text.strip():
        raise RuntimeError("Tesseract returned no text")

    return text.strip()


def _extract_image(path: Path, ocr_config: dict[str, Any]) -> OcrResult:
    """OCR one image file directory without creating an intermediate raster."""
    with Image.open(path) as image:
        text = _ocr_image(image.convert("RGB"), ocr_config)

    return OcrResult(raw_text=text, num_pages=1)


def _extract_pdf(path: Path, ocr_config: dict[str, Any]) -> OcrResult:
    """Render every PDF page with Poppler, then OCR each rendered page."""
    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm is None:
        raise RuntimeError("Poppler binary not found: pdftoppm")

    with tempfile.TemporaryDirectory(prefix="docextract-") as temp_dir:
        output_prefix = Path(temp_dir) / "page"

        command = [
            pdftoppm,
            "-png",
            "-r",
            str(ocr_config["dpi"]),
            str(path),
            str(output_prefix),
        ]

        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as error:
            message = error.stderr.strip() or "pdftoppm failed"
            raise RuntimeError(message) from error

        page_paths = sorted(Path(temp_dir).glob("page-*.png"))
        if not page_paths:
            raise RuntimeError("pdftoppm produced no page images")

        page_text = []
        for page_path in page_paths:
            with Image.open(page_path) as image:
                page_text.append(_ocr_image(image.convert("RGB"), ocr_config))

    return OcrResult(
        raw_text="\n\n".join(page_text),
        num_pages=len(page_paths)
    )


def extract(path: str | Path, config: dict[str, Any]) -> OcrResult:
    """OCR a supported image or PDF and fail clearly for invalid input."""
    input_path = Path(path)

    if not input_path.is_file():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    suffix = input_path.suffix.lower()
    if suffix not in SUPPORTED_FILES:
        supported = ", ".join(sorted(SUPPORTED_FILES))
        raise ValueError(f"Unsupported file type '{suffix}'. Supported: {supported}")

    ocr_config = _validate_config(config)

    tesseract_cmd = ocr_config["tesseract_cmd"]
    if shutil.which(tesseract_cmd) is None:
        raise RuntimeError(f"Tesseract binary not found: {tesseract_cmd}")

    if suffix in SUPPORTED_IMAGES:
        return _extract_image(input_path, ocr_config)

    return _extract_pdf(input_path, ocr_config)