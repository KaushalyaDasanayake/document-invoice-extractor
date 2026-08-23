from fastapi import FastAPI, File, UploadFile, Depends, Request, HTTPException

from docextract.api.deps import get_ocr_engine
from docextract.utils.logging import new_request_id, get_logger
from docextract.schemas.response import ExtractResponse

logger = get_logger(__name__)

app = FastAPI(title="Invoice Extractor API")

# dependency that runs before all routes in the app. fastapi runs this once at startup(no request) good for config load.
@app.middleware("http")
async def add_request_id_and_log(request, call_next):
    request_id = new_request_id()
    logger.info(f"request={request_id} method={request.method} path={request.url.path}")
    response = await call_next(request)
    logger.info(f"request={request_id} response_status={response.status_code}")
    return response


@app.get("/health")
async def health():
    """Liveness check: is the process up?"""
    return {"status": "ok"}


@app.get("/ready")
async def ready(engine=Depends(get_ocr_engine)):
    """Readiness check: can we actually do OCR?"""
    try:
        engine # triggers config/tesseract val
    except Exception:
        raise HTTPException(status_code=503, detail="OCR not ready")
    return {"status": "ready"}


@app.post("/v1/extract", response_model=ExtractResponse)
async def extract_route(
    request: Request,
    file: UploadFile = File(...),
    engine=Depends(get_ocr_engine) # injected
):
    """Extract raw text from an uploaded invoice."""
    content = await file.read()
    result = engine(content) 
    return ExtractResponse(raw_text=result.raw_text, num_pages=result.num_pages)

