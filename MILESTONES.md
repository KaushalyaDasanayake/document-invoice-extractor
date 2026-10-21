# Project 1: Document Data Extractor (Invoices)
## Milestones + Folder Structure

Follows the same conventions as your monorepo and news-nlp-classifier:
FastAPI + pydantic v2, `configs/base.yaml`, `src/<pkg>/` layout, `tests/` with
anyio/httpx, `golden_set/`, `eval/metrics.json`, README with a run order.

Goal: **PDF/image invoice -> OCR -> field extraction (NER + regex) ->
schema-validated JSON -> editable UI -> CSV/Excel/PDF export**, with field-level
precision/recall on a golden set.

Map of roadmap weeks to each milestone:
- **w15** long-text strategies (chunking a whole invoice page)
- **w16** NER / token classification (the core extraction model)
- **w24 / w30** security, PII redaction, governance, retention
- **w25 / w26** API versioning, async job queue, concurrency
- **w27** observability / structured logging / tracing

---

## Folder structure
```
document-invoice-extractor/
  configs/
    base.yaml                  # model paths, OCR langs, field regexes, thresholds
  data/
    raw/                       # scanned invoices (PDF/PNG/JPG) - gitignored
    processed/                 # OCR text + extracted JSON per doc - gitignored
    samples/                   # 2-3 tiny public/fake invoices for the demo
  golden_set/
    invoices_v1.json           # golden: expected fields per sample invoice
  eval/
    metrics.json               # field-level precision/recall, per-field, saved here
  docker/
    Dockerfile                 # tesseract + python + deps
    docker-compose.yml         # api + postgres + (optionally) worker
  src/docextract/
    api/
      main.py                  # FastAPI app, /health /ready /v1/extract /v1/jobs
      deps.py                  # request_id, config injection
    schemas/
      request.py               # ExtractRequest (file, options)
      response.py              # InvoiceResult, InvoicesResponse, FieldValue
    ocr/
      engine.py                # tesseract wrapper (image/pdf -> text + coords)
      preprocess.py            # deskew, denoise, contrast (OpenCV)
    ner/
      model.py                 # HF token-classification model wrapper (w16)
      predict.py               # run NER, return token/offset preds
    fields/
      extractors.py            # per-field regex/NER/rule logic
      normalize.py             # dates, currency, amounts -> canonical types
    postprocess/
      merge.py                 # combine NER + regex into one field map
      validate.py              # pydantic schema validation, confidence thresholds
      redact.py                # PII redaction (w24/w30)
    config.py                  # load configs/base.yaml
    utils/
      logging.py               # structured JSON logging w/ request_id (w27)
      async_queue.py           # job queue abstraction (w25/w26)
  tests/
    unit/
      test_fields_extractors.py
      test_normalize.py
      test_validate.py
      test_redact.py
    integration/
      test_health.py
      test_extract_success.py     # fake engine injected
      test_export.py
  ui/
    App.tsx / components/...      # editable table, export buttons
  scripts/
    build_golden_set.py           # helper to assemble golden JSON
    run_eval.py                   # field-level P/R against golden set
    demo_gen.py                   # generate sample invoices for demo
  pyproject.toml                  # package + ruff + pytest config (mirror newsclf)
  requirements.txt
  README.md                       # run order + example output
```

---

## Milestones (ordered, each independently shippable)

### M1 - Vertical slice (OCR -> text -> reply) "proves the pipeline"
- [ ] FastAPI app with `/health`, `/ready`, `/v1/extract`
- [ ] `ocr/engine.py` runs Tesseract on an uploaded image/PDF and returns raw
      text (start with a real scanned sample invoice in `data/samples/`)
- [ ] `/v1/extract` returns `{ raw_text, num_pages }`
- [ ] config-driven Tesseract language + psm settings in `configs/base.yaml`
- **Demo:** POST one sample invoice -> text comes back.

# Confidence per page is intentionally deferred to the storage milestone (M5),

### M2 - Field regex extraction (no ML yet)
- [ ] `fields/extractors.py`: regex/NER-lite for invoice#, date, vendor, totals,
      line items
- [ ] `fields/normalize.py`: canonicalize dates, currency, amounts
- [ ] pydantic schema `InvoiceResult` in `schemas/response.py`
- [ ] unit tests for extractors + normalization (`eval` on the golden set, show
      initial field-level P/R to establish the baseline)
- **Week practices:** w24/w30 (token hygiene, input validation), w15 (handling
      long invoice text via chunking).

### M3 - NER model for field extraction (the core ML)
- [ ] `ner/model.py` + `ner/predict.py` wrapping a HF token-classification model
      (reuse the token -> offset alignment approach from `week_16_ner_api`)
- [ ] Train/evaluate a domain NER (invoice fields) or fine-tune on a public
      invoice/forms dataset; report entity-level F1 in `eval/metrics.json`
- [ ] fallback wiring: if NER is unsure/low-confidence, fall back to regex
- **Week practices:** w16 (NER token classification, wordpiece alignment,
      entity-level F1), w14 (fine-tune practice, macro metrics).

### M4 - Merge + validation + confidence
- [ ] `postprocess/merge.py`: combine NER spans + regex into one field map
      (dedupe, resolve conflicts by confidence)
- [ ] `postprocess/validate.py`: pydantic validation, per-field confidence
      threshold, mark low-confidence fields
- [ ] field-level precision/recall on the golden set; save to `eval/metrics.json`
- **Week practices:** w15 stage-merge/long-text decisions, w14 metrics discipline.

### M5 - Async job queue + storage
- [ ] `utils/async_queue.py`: job-based extraction (submit job id, poll status)
      for longer invoices; OR BackgroundTasks for quick ones
- [ ] persist extracted results to Postgres (users/requests/results tables)
- [ ] `/v1/jobs/{id}` status endpoint
- **Week practices:** w25/w26 (API versioning, async jobs, concurrency).

### M6 - PII / security / retention
- [ ] `postprocess/redact.py`: redact sensitive fields (customer PII) before
      storage/logging
- [ ] input validation + size limits, auth (API key), no PII in logs
- [ ] retention/deletion policy for stored invoices
- **Week practices:** w24/w30 (security, PII, governance, retention).

### M7 - UI + export
- [ ] `ui/`: upload -> editable table (correct/wrong fields) -> export
      CSV/Excel/PDF
- [ ] export endpoints in the API
- **Demo:** full flow: upload a sample -> edit -> export.

### M8 - Production hardening + README
- [ ] Dockerfile + docker-compose (`api` + `postgres`)
- [ ] structured JSON logging + request_id end-to-end (w27 observability)
- [ ] CI (GitHub Actions): lint + unit tests + golden-set eval gate
- [ ] README with run order, example output, and a "recruiter can scan in 2
      minutes" case study with field-level P/R numbers
- **Definition of done:** docker compose up reproduces the service; CI runs lint
  + tests + eval; golden set passes.

---

## Notes / scope guards
- Keep the golden set frozen once built; only add new invoices on purpose.
- Publish real numbers (field-level precision/recall) even if below target;
  record failure modes rather than fudging.
- The differentiator is **full product delivery** (UI + queue + DB + deploy),
  which is your edge over researchers. Keep M7/M8 real, not skipped.
- Start every milestone with a runnable test so "done" is verifiable.



M0 – Golden set + demo samples
- data/samples/: 5–10 real-looking but synthetic invoices (PDF + PNG), representative: different vendors/templates, currencies, multi-page
- data/golden/invoices_v1.json: per-sample ground truth: fields, line items, bounding boxes where useful
- tests/test_golden_set.py: assert each sample JSON loads, schema validates
- configs/golden.yaml or similar: path + schema version + regeneration flag
- Done when: make golden builds a fresh copy, every sample has golden JSON, and the golden set is committed so CI can use it.
M1 - API skeleton + upload + raw OCR (vertical slice)
- FastAPI app with POST /v1/extract (multipart upload → { call_id, status })
- POST /v1/upload, GET /v1/jobs/{id} (async job pattern)
- OCR on uploaded PDF/image; store raw text + page count + confidence
- minimal InvoiceResult schema: invoice_no, date, vendor, total
- /v1/health + request_id logging (w27 observability seed)
- auth: API key check (w30)
M1 - Golden set + vertical extraction
- scripts/gen_invoices.py — generates the golden set (5–10 invoices) once
- scripts/gen_golden_set.py — builds JSON ground truth, e.g. invoice_no,
    date, vendor, line items
- golden set committed + frozen (a test fixture, not art)
- first vertical slice: POST /extract, loads file, OCR, regex-fill invoice_no,
    date, vendor, line_items, total; returns JSON
- evaluate on golden_set/invoices_v1.json: report field-level P/R and
    "cost per invoice" (time + compute)
- README: "How I built it quick" story
- Week practices: w12 (strategy), w17 (OSS/data licensing), w21 (packaging,
    local deps pinned)
M2 - Production-ize extraction (Docker + API hardening + eval gate)
- docker/ (Dockerfile + compose) with Postgres + API + eval job
- /v1/extract, /v1/eval endpoints (accept invoice, return JSON; run golden eval on demand)
- request_id + structured JSON logs (w27 observability)
- schema validation + size limits on uploads
- published P/R on the golden set; gate = >=80% exact field P/R, no regressions on frozen
    invoice_v1 set
- auth via API key (w24), rate limiting
- Week practices: w14 (log), 15 ( )+wrap, 27 (observability)
M5 - Batch + monitoring
- /v1/jobs async queue for batch (Celery/Redis or in-proc queue)
- per-invoice status, retries, timeout, dead-letter queue
- worker crash-safe: resume, re-enqueue, idempotency key per invoice
- open-feedback endpoint: client corrects extracted JSON (right/wrong)
- store corrections as labeled examples; plug into w28 practice as
    eval-gate inputs
- dashboard: counts of fields wrong per template/vendor (daily)
- Week practices: w24 (versioning), w25 (production), w28 (eval gates CI)
- Exit: batch endpoint stable, a batch of 100 invoices from golden run clean
M6 - Async architecture + queue (upload → job → result)
- POST /v1/jobs (accept raw upload, store to disk/S3, enqueue), pollable
    GET /v1/jobs/{id} returning status + confidence
- Redis (w27 queues) + worker for OCR/extraction; idempotent job retries
- concurrency, backpressure, timeout policy per job (retries w/ backoff)
- rate limiting per API key; job state transitions + audit trail
- POST /v1/jobs/bulk enqueue list of invoices (batch)
- as M3 (async queue of the v1 path)** over $0.5
- DECISION vs M4 vs M5: if invoice extraction is THE deliverable, async jobs
are the right scale; if it's demo-only, M5 sync endpoints are fine. Decide
with: "Would a client submit 1000 invoices and walk away?" If yes, M3.
M4 - Sense-check evaluation on invoices (P/R per field, P/R per vendor)
- Workbench aims: parameter sweep dashboard ("offset: -1 vs 0", "date yyyy-mm-dd vs
dd/mm/yyyy"), and a sweep_report.json comparing regex vs model vs merge on the
golden set.
- Deliverables:
- eval_mer (eval_mer) : field-level precision / recall per field on golden set
- dashboards per pattern + a "regex vs model vs merged" comparison (currently a sweep)
- report saved to golden_set/eval_report.json
M4 - Async job queue + Postgres persistence
- Goal: queue long-running extraction, store results
- Deliverables:
- worker.py + queue (Redis/RQ or Celery; or simpler: threading + job table)
- Poll GET /v1/jobs/{id} endpoint
- store to Postgres (invoices, fields extracted, source file)
- Week practice: async job semantics (w22)
- Doc flip: the same queue + DB lets you log every extraction (source hash, model
version, per-field confidences) — that's your audit trail / eval trace.
- This is the data engine for M6
M4 - Robust validation + flagging (confidence + cross-field sanity)
- confidence per field; flag low-confidence & inconsistent fields
- typo/format normalization per field type (date, currency, number)
- cross-field checks (e.g., total != sum(line items)) paid off to the user instead of hallucinating
- Week practices: w15 long-context, w18 prompt caching*
M5 - Deploy: FastAPI + Postgres + Docker (your edge, rarely demoed)
- FastAPI + Postgres (via docker compose): upload, OCR, job status, results table
- extraction + job tables, API key auth, per-user storage quotas
- POST /v1/extract/invoice -> 202 Async 202 -> GET status -> GET result
- Schema: invoices (id, user_id, filename, status, raw_text, data JSONB, pii:bool)
- rate limiting + length caps; content-type validation
- Demo script: scripts/demo_golden.py pushes M0 invoices at the API, shows
the returned JSON, and prints pass/fail against the golden set. Seeded with
reproduciable redactable fixtures. This is the README's "try me now".
Milestone M3. Async queue.
