---
title: Invoice Data Extractor Studio
emoji: 🧾
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 4.19.2
app_file: app.py
pinned: false
---

# Document Data Extractor (`docextract`)

A production-style document invoice extractor that processes scanned PDFs and image files via OCR, extracts structured invoice fields, validates contracts with Pydantic v2, computes confidence scores and mathematical sanity checks, supports PII redaction, and provides CSV/JSON export endpoints.

---

## 1. Quick Start

### Prerequisites
- Python 3.10+
- Tesseract OCR (`sudo apt-get install tesseract-ocr tesseract-ocr-eng`)
- Poppler utilities for PDF rasterization (`sudo apt-get install poppler-utils`)

### Installation
```bash
# Clone the repository
git clone <repo-url>
cd document-invoice-extractor

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install package and dependencies
pip install -e ".[dev]"
```

### Running the API Server
```bash
uvicorn docextract.api.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 2. API Endpoints

All protected endpoints require the `X-API-Key` header (default development key: `dev-key-change-in-prod`, configurable via `DOCEXTRACT_API_KEY`).

| Method | Path | Description | Protected |
|---|---|---|---|
| `GET` | `/health` | Liveness check (process alive) | No |
| `GET` | `/ready` | Readiness check (validates OCR engine & dependencies) | No |
| `POST` | `/v1/extract` | Upload invoice PDF/PNG/JPG -> OCR + structured JSON extraction | Yes |
| `POST` | `/v1/export/csv` | Convert structured invoice into itemized CSV file | Yes |
| `POST` | `/v1/export/json` | Return canonical invoice JSON payload | Yes |

### Example Usage: Extract Invoice
```bash
curl -X POST "http://localhost:8000/v1/extract" \
  -H "X-API-Key: dev-key-change-in-prod" \
  -F "file=@golden_set/inputs/invoice_001.pdf"
```

### Example Usage: Extract with PII Redaction
```bash
curl -X POST "http://localhost:8000/v1/extract?redact=true" \
  -H "X-API-Key: dev-key-change-in-prod" \
  -F "file=@golden_set/inputs/invoice_001.pdf"
```

---

## 3. Evaluation & Quality Metrics

We test the end-to-end pipeline against a frozen golden set of 8 multi-template synthetic invoices across various currencies (USD, EUR, CAD, JPY, ZAR) and layouts (single-page and multi-page).

To run the golden set evaluation:
```bash
# Generate predictions and compute Precision & Recall metrics
python scripts/run_eval.py --predictions-dir eval/predictions
```

### Benchmark Results on Frozen Golden Set
```text
Evaluated 8 samples
Precision: 0.808 (80.8%)
Recall:    0.618 (61.8%)
```

Key field performance:
- `invoice_number`: 100% (8/8)
- `invoice_date`: 100% (8/8)
- `due_date`: 100% (8/8)
- `vendor_name`: 100% (8/8)
- `vendor_address`: 100% (8/8)
- `customer_name`: 100% (8/8)
- `subtotal`: 100% (8/8)
- `line_items`: 75% (6/8)

---

## 4. Running Tests & Linting

```bash
# Run unit and integration tests (excluding slow OCR by default)
pytest

# Run full test suite including live OCR tests
pytest -m ""

# Run ruff linter
ruff check .
```

---

## 5. Docker Deployment

```bash
# Build and run with docker compose
docker compose up --build -d

# Check health
curl http://localhost:8000/health
```
