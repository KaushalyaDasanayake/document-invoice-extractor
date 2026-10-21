import csv
import io
import tempfile
from pathlib import Path

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
)
from fastapi.responses import HTMLResponse

from docextract.api.auth import require_api_key
from docextract.api.deps import OCRDep
from docextract.postprocess.merge import merge_ner_and_regex
from docextract.postprocess.redact import redact_invoice_data
from docextract.postprocess.validate import (
    calculate_field_confidences,
    validate_cross_fields,
)
from docextract.schemas.invoice import ExtractionResult
from docextract.schemas.response import ExtractResponse
from docextract.utils.async_queue import GLOBAL_QUEUE
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


@app.get("/", response_class=HTMLResponse)
async def serve_ui() -> HTMLResponse:
    """Serve the M7 web interface studio."""
    ui_path = Path(__file__).resolve().parents[3] / "ui" / "index.html"
    if ui_path.exists():
        return HTMLResponse(content=ui_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Invoice Extractor API</h1><p>UI not found</p>")


@app.post("/v1/extract", response_model=ExtractResponse, dependencies=[Depends(require_api_key)])
async def extract_route(
    file: UploadFile = File(...),  # noqa: B008
    engine: OCRDep = None,  # injected by FastAPI via dependency
    redact: bool = Query(False, description="Whether to redact customer PII"),
) -> ExtractResponse:
    # write the upload to a temp file
    suffix = Path(file.filename or "upload").suffix or ".bin"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        tmp.write(await file.read())
        tmp.flush()
        result = engine(tmp.name)

    extracted_data = merge_ner_and_regex(result.raw_text)
    confidences = calculate_field_confidences(extracted_data)
    warnings = validate_cross_fields(extracted_data)

    if redact:
        extracted_data = redact_invoice_data(extracted_data)

    invoice_obj = ExtractionResult.model_validate(extracted_data)

    return ExtractResponse(
        raw_text=result.raw_text,
        num_pages=result.num_pages,
        invoice=invoice_obj,
        confidences=confidences,
        warnings=warnings,
    )


def _process_job_task(job_id: str, file_bytes: bytes, filename: str, engine) -> None:
    try:
        suffix = Path(filename).suffix or ".bin"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
            tmp.write(file_bytes)
            tmp.flush()
            result = engine(tmp.name)

        extracted_data = merge_ner_and_regex(result.raw_text)
        confidences = calculate_field_confidences(extracted_data)
        warnings = validate_cross_fields(extracted_data)
        invoice_obj = ExtractionResult.model_validate(extracted_data)

        GLOBAL_QUEUE.update_job_success(
            job_id,
            {
                "raw_text": result.raw_text,
                "num_pages": result.num_pages,
                "invoice": invoice_obj.model_dump(),
                "confidences": confidences,
                "warnings": warnings,
            },
        )
    except Exception as exc:
        logger.error(f"Async job {job_id} failed: {exc}")
        GLOBAL_QUEUE.update_job_failed(job_id, str(exc))


@app.post("/v1/jobs", dependencies=[Depends(require_api_key)])
async def submit_job_route(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),  # noqa: B008
    engine: OCRDep = None,
) -> dict[str, str]:
    """Submit invoice extraction as an asynchronous background job (M5)."""
    file_bytes = await file.read()
    filename = file.filename or "invoice.pdf"
    job_id = GLOBAL_QUEUE.create_job(filename)

    background_tasks.add_task(_process_job_task, job_id, file_bytes, filename, engine)
    return {"job_id": job_id, "status": "pending"}


@app.get("/v1/jobs/{job_id}", dependencies=[Depends(require_api_key)])
async def get_job_route(job_id: str) -> dict:
    """Poll status and result of an async extraction job (M5)."""
    job = GLOBAL_QUEUE.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job.job_id,
        "status": job.status,
        "filename": job.filename,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
        "result": job.result,
        "error": job.error,
    }


@app.post("/v1/export/csv", dependencies=[Depends(require_api_key)])
async def export_csv_route(invoice: ExtractionResult) -> Response:
    """Export itemized line items and totals to CSV format."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Metadata header
    writer.writerow(["Invoice Number", invoice.invoice_number])
    writer.writerow(["Invoice Date", invoice.invoice_date])
    writer.writerow(["Vendor", invoice.vendor_name])
    writer.writerow(["Customer", invoice.customer_name])
    writer.writerow(["Currency", invoice.currency])
    writer.writerow([])

    # Table columns
    writer.writerow(["Description", "Quantity", "Unit Price", "Line Total"])
    for item in invoice.line_items:
        writer.writerow([item.description, item.quantity, item.unit_price, item.line_total])

    writer.writerow([])
    writer.writerow(["Subtotal", invoice.totals.subtotal])
    writer.writerow(["Tax", invoice.totals.tax])
    writer.writerow(["Shipping", invoice.totals.shipping])
    writer.writerow(["Grand Total", invoice.totals.grand_total])

    csv_content = output.getvalue()
    filename = f"{invoice.invoice_number or 'invoice'}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/v1/export/json", dependencies=[Depends(require_api_key)])
async def export_json_route(invoice: ExtractionResult) -> dict:
    """Export clean canonical invoice dictionary."""
    return invoice.model_dump()


