import tempfile
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile

from docextract.api.auth import require_api_key
from docextract.api.deps import OCRDep
from docextract.fields.extractors import extract_invoice
from docextract.schemas.invoice import ExtractionResult
from docextract.schemas.response import ExtractResponse
from docextract.utils.logging import get_logger, new_request_id

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
async def ready(engine: OCRDep) -> dict[str, str]:
    """Readiness check: can we actually do OCR?"""
    if engine is None:
        raise HTTPException(status_code=503, detail="OCR not ready: engine unavailable")
    return {"status": "ready"}



@app.post("/v1/extract", response_model=ExtractResponse, dependencies=[Depends(require_api_key)])
async def extract_route(
    file: UploadFile = File(...), # noqa: B008
    engine: OCRDep = None,  # injected by FastAPI via dependency
) -> ExtractResponse:
    # write the upload to a temp file
    suffix = Path(file.filename or "upload").suffix or ".bin"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        tmp.write(await file.read())
        tmp.flush()
        result = engine(tmp.name)

        extracted_data = extract_invoice(result.raw_text)
        invoice_obj = ExtractionResult.model_validate(extracted_data)
    return ExtractResponse(
        raw_text=result.raw_text, 
        num_pages=result.num_pages,
        invoice=invoice_obj
        )
