"""Shared fixtures for the test suite.

The OCR engine calls `shutil.which()` to confirm tesseract/pdftoppm exist
before running. That binary is not present on every machine (e.g. CI), so
unit tests would fail on the binary check before ever testing the logic
they care about. This autouse fixture fakes the existence of both binaries
so unit tests run anywhere, while the real-OCR smoke test (marked `slow`)
still exercises the actual installation.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _fake_external_binaries(monkeypatch):
    """Pretend tesseract and pdftoppm are installed for every unit test."""

    def fake_which(name: str, *args, **kwargs) -> str | None:
        # The engine checks tesseract by its config path (e.g.
        # "/usr/bin/tesseract") and poppler by bare name ("pdftoppm").
        if name == "pdftoppm":
            return "/usr/bin/pdftoppm"
        if name.endswith("tesseract"):
            return "/usr/bin/tesseract"
        return None

    monkeypatch.setattr("docextract.ocr.engine.shutil.which", fake_which)