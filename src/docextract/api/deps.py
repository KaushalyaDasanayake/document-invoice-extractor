"""Application dependencies"""

from __future__ import annotations
from pathlib import Path
from fastapi import Depends
from typing import Annotated, Callable

from docextract.ocr.engine import extract as ocr_extract, OcrResult
from docextract.config import load_config

# The type every caller uses. A fake engine must match this signature.
OCRCallable = Callable[[str | Path], OcrResult]


def _build_engine() -> OCRCallable:
    """Build and return the real OCR engine bound to the loaded config.

    The config is loaded once here, not per request. Returns a plain
    function with the same call shape the routes and the fake use.
    """
    config = load_config()
    return lambda path: ocr_extract(path, config)


def get_ocr_engine() -> OCRCallable:
    """FastAPI dependency that injects the OCR engine into routes.

    Tests override this dependency with a fake callable.
    """
    return _build_engine()


# type alias so route signature stay readable
OCRDep = Annotated[OCRCallable, Depends(get_ocr_engine)]
