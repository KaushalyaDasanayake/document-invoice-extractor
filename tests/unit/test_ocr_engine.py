"""Tests for the OCR engine (image + PDF branches)."""

from __future__ import annotations

from pathlib import Path

import pytesseract  # referenced via monkeypatched module attr
import pytest
from PIL import Image, ImageDraw

from docextract.ocr.engine import OcrResult, extract

VALID_CONFIG = {
    "ocr": {
        "lang": "eng",
        "psm": 6,
        "dpi": 300,
        "tesseract_cmd": "/usr/bin/tesseract",
    }
}


@pytest.fixture
def png_image(tmp_path: Path) -> Path:
    """A real 2x2 PNG on disk that PIL can open."""
    path = tmp_path / "invoice.png"
    image = Image.new("RGB", (2, 2), color="white")
    ImageDraw.Draw(image)
    image.save(path)
    return path


def _fake_pdftoppm_run(monkeypatch, image: Image.Image, pages: int) -> None:
    """Patch subprocess.run so it writes N fake page rasters like pdftoppm."""

    def fake_run(command, **kwargs):
        prefix = command[-1]
        for index in range(1, pages + 1):
            output = Path(f"{prefix}-{index}.png")
            image.save(output)

    monkeypatch.setattr("docextract.ocr.engine.subprocess.run", fake_run)


# ----------------------------- config ------------------------------
# `extract` validates the file on disk before validating config
# config tests share a real temp file as the input.


def test_valid_config_accepted(monkeypatch, png_image: Path) -> None:
    monkeypatch.setattr(pytesseract, "image_to_string", lambda *a, **k: "hello")
    result = extract(png_image, VALID_CONFIG)
    assert result.num_pages == 1


@pytest.mark.parametrize(
    "mutate, expected",
    [
        ("missing_ocr", "only the 'ocr'"),
        ("extra_key", "only the 'ocr'"),
        ("bad_psm", "ocr.psm"),
        ("bad_dpi", "ocr.dpi"),
        ("empty_lang", "ocr.lang"),
    ],
)
def test_invalid_config_rejected(
    mutate: str, expected: str, png_image: Path
) -> None:
    if mutate == "missing_ocr":
        config: dict = {}
    elif mutate == "extra_key":
        config = dict(VALID_CONFIG)
        config["extra"] = True
    elif mutate == "bad_psm":
        config = {"ocr": dict(VALID_CONFIG["ocr"], psm=99)}
    elif mutate == "bad_dpi":
        config = {"ocr": dict(VALID_CONFIG["ocr"], dpi=0)}
    else:  # empty_lang
        config = {"ocr": dict(VALID_CONFIG["ocr"], lang="  ")}

    with pytest.raises(ValueError, match=expected):
        extract(png_image, config)


# ----------------------------- input ---------------------------------


def test_missing_file_raises_file_not_found(monkeypatch) -> None:
    monkeypatch.setattr(pytesseract, "image_to_string", lambda *a, **k: "x")
    with pytest.raises(FileNotFoundError):
        extract("does_not_exist.png", VALID_CONFIG)


def test_unsupported_extension_rejected(monkeypatch, tmp_path: Path) -> None:
    bad = tmp_path / "invoice.txt"
    bad.touch()
    monkeypatch.setattr(pytesseract, "image_to_string", lambda *a, **k: "x")
    with pytest.raises(ValueError, match="Unsupported file type"):
        extract(bad, VALID_CONFIG)


def test_missing_tesseract_binary(monkeypatch, png_image: Path) -> None:
    monkeypatch.setattr("docextract.ocr.engine.shutil.which", lambda _name: None)
    with pytest.raises(RuntimeError, match="Tesseract binary not found"):
        extract(png_image, VALID_CONFIG)


# ------------------------------ image --------------------------------


def test_extract_image_returns_text(monkeypatch, png_image: Path) -> None:
    monkeypatch.setattr(
        pytesseract, "image_to_string", lambda *a, **k: "line1\nline2"
    )
    result = extract(png_image, VALID_CONFIG)

    assert isinstance(result, OcrResult)
    assert result.num_pages == 1
    assert result.raw_text == "line1\nline2"


def test_extract_image_strips_whitespace(monkeypatch, png_image: Path) -> None:
    monkeypatch.setattr(
        pytesseract, "image_to_string", lambda *a, **k: "  padded  \n"
    )
    result = extract(png_image, VALID_CONFIG)
    assert result.raw_text == "padded"


def test_extract_image_empty_text_raises(monkeypatch, png_image: Path) -> None:
    monkeypatch.setattr(pytesseract, "image_to_string", lambda *a, **k: "   ")
    with pytest.raises(RuntimeError, match="returned no text"):
        extract(png_image, VALID_CONFIG)


# ------------------------------ pdf ------------------------------------


def _make_image() -> Image.Image:
    image = Image.new("RGB", (2, 2), color="white")
    ImageDraw.Draw(image)
    return image


@pytest.fixture
def pdf_file(tmp_path: Path) -> Path:
    """A real PDF file on disk so the engine's existence check passes.

    The engine never reads the contents for a .pdf input (pdftoppm does),
    so a minimal placeholder is enough; the content is meaningless here.
    """
    path = tmp_path / "invoice.pdf"
    path.write_bytes(b"%PDF-1.4 fake but real-enough for the existence check")
    return path


def test_extract_pdf_multipage(
    monkeypatch, pdf_file: Path
) -> None:
    fake = _make_image()
    _fake_pdftoppm_run(monkeypatch, fake, pages=2)
    monkeypatch.setattr(
        pytesseract, "image_to_string", lambda *a, **k: "page text"
    )

    result = extract(pdf_file, VALID_CONFIG)

    # Two pages -> two rendered rasters, joined by a blank line.
    assert result.num_pages == 2
    assert result.raw_text == "page text\n\npage text"


def test_extract_pdf_missing_poppler(monkeypatch, pdf_file: Path) -> None:
    def fake_which(name: str) -> str | None:
        # tesseract_cmd resolves, pdftoppm does not.
        if name == "pdftoppm":
            return None
        return "/usr/bin/tesseract"

    monkeypatch.setattr("docextract.ocr.engine.shutil.which", fake_which)
    monkeypatch.setattr(pytesseract, "image_to_string", lambda *a, **k: "x")
    with pytest.raises(RuntimeError, match="[Pp]oppler"):
        extract(pdf_file, VALID_CONFIG)
