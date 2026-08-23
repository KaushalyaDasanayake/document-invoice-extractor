from fastapi import Depends, Request
from typing import Annotated

from docextract.ocr.engine import extract as ocr_extract, OcrResult
from docextract.config import load_config


def get_ocr_engine():
    """Build and return the real OCR engine(Tesseract + config).
    
    Injected as the default so routes don't know where OCR logic is. Tests replace this dependency with a fake that returns fast.
    """
    config = load_config() # returns base.yaml dict
    return lambda path, cfg=config: ocr_extract(path, cfg)


# type alias so route signature stay readable
OCRDep = Annotated[OcrResult, Depends(get_ocr_engine)]