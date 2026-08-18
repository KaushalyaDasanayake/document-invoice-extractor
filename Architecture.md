## Plan: Invoice NER + Regex extractor → Pydantic schema

### Architecture
Invoice PDF/image
      ↓
Preprocess (OpenCV: deskew/denoise/upscale)
      ↓
OCR (Tesseract) → raw text + word boxes
      ↓
Extractor (regex + rules) -------------------------------------> extracted fields
      ↓
NER (HF token-classification, can be fine-tuned on invoice tokens later)
      ↓
Merge (rule + NER) with confidence + Pydantic validation
      ↓
JSON ((raw + processed) log for eval/debug), PII masking optional


**Milestone plan:**
M2: OCR (Tesseract) works and output text is saved
M4: Rule/regex baseline with confidence
M8: NER end-to-end (TinyBERT) + fallback
M12: Deployment (Docker, API), monitoring
M16: PII, VLM fallback? maybe