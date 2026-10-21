import io
import json
import os
import sys
import tempfile
from pathlib import Path

# Add src to Python path so docextract package is discoverable on cloud environments
ROOT = Path(__file__).resolve().parent
src_path = str(ROOT / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import pandas as pd
import streamlit as st

from docextract.config import load_config
from docextract.ocr.engine import extract as ocr_extract
from docextract.postprocess.merge import merge_ner_and_regex
from docextract.postprocess.redact import redact_invoice_data
from docextract.postprocess.validate import (
    calculate_field_confidences,
    validate_cross_fields,
)
from docextract.schemas.invoice import ExtractionResult

st.set_page_config(
    page_title="Invoice Data Extractor",
    page_icon="🧾",
    layout="wide",
)

st.title("🧾 Invoice Data Extractor Studio")
st.caption("Automated OCR, Entity Extraction, Cross-field Validation & CSV/JSON Export")

# Sidebar settings
st.sidebar.header("Settings")
redact_pii = st.sidebar.checkbox("Redact Customer PII", value=False)
show_ocr_raw = st.sidebar.checkbox("Show Raw OCR Text", value=False)

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    **Tech Stack:**
    - Python 3.10+
    - Tesseract OCR & Poppler
    - Pydantic v2 Contract Validation
    - Regex & Heuristic NER Engine
    """
)

uploaded_file = st.file_uploader(
    "Upload Invoice (PDF, PNG, JPG)",
    type=["pdf", "png", "jpg", "jpeg"],
    help="Supports single-page and multi-page invoices.",
)

if uploaded_file is not None:
    suffix = Path(uploaded_file.name).suffix or ".bin"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    with st.spinner("Processing OCR and extracting structured fields..."):
        try:
            cfg = load_config()
            ocr_result = ocr_extract(tmp_path, cfg)
            raw_text = ocr_result.raw_text

            extracted_data = merge_ner_and_regex(raw_text)
            confidences = calculate_field_confidences(extracted_data)
            warnings = validate_cross_fields(extracted_data)

            if redact_pii:
                extracted_data = redact_invoice_data(extracted_data)

            invoice = ExtractionResult.model_validate(extracted_data)

            # Display Validation Warnings
            if warnings:
                for w in warnings:
                    st.warning(f"⚠️ {w}")
            else:
                st.success("✅ Extraction passed all cross-field arithmetic checks!")

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Invoice #", invoice.invoice_number)
            col2.metric("Currency", invoice.currency)
            col3.metric("Date", invoice.invoice_date)
            col4.metric("Grand Total", f"{invoice.currency} {invoice.totals.grand_total:,.2f}")

            st.markdown("### Party Details")
            p_col1, p_col2 = st.columns(2)
            with p_col1:
                st.markdown(f"**Vendor:** {invoice.vendor_name}")
                st.caption(invoice.vendor_address or "No address detected")
            with p_col2:
                st.markdown(f"**Customer:** {invoice.customer_name}")
                st.caption(invoice.customer_address or "No address detected")

            st.markdown("### Line Items")
            items_data = [
                {
                    "Description": item.description,
                    "Quantity": item.quantity,
                    "Unit Price": item.unit_price,
                    "Line Total": item.line_total,
                }
                for item in invoice.line_items
            ]
            df_items = pd.DataFrame(items_data)
            st.dataframe(df_items, use_container_width=True)

            t_col1, t_col2, t_col3, t_col4 = st.columns(4)
            t_col1.metric("Subtotal", f"{invoice.totals.subtotal:,.2f}")
            t_col2.metric("Tax", f"{invoice.totals.tax:,.2f}")
            t_col3.metric("Shipping", f"{invoice.totals.shipping:,.2f}")
            t_col4.metric("Grand Total", f"{invoice.totals.grand_total:,.2f}")

            # Export actions
            st.markdown("### Export")
            exp_col1, exp_col2 = st.columns([1, 1])

            # CSV Export
            csv_buf = io.StringIO()
            csv_buf.write(f"Invoice Number,{invoice.invoice_number}\n")
            csv_buf.write(f"Vendor,{invoice.vendor_name}\n")
            csv_buf.write(f"Customer,{invoice.customer_name}\n")
            csv_buf.write(f"Date,{invoice.invoice_date}\n\n")
            df_items.to_csv(csv_buf, index=False)
            csv_buf.write(f"\nSubtotal,{invoice.totals.subtotal}\n")
            csv_buf.write(f"Tax,{invoice.totals.tax}\n")
            csv_buf.write(f"Shipping,{invoice.totals.shipping}\n")
            csv_buf.write(f"Grand Total,{invoice.totals.grand_total}\n")

            exp_col1.download_button(
                label="📥 Download CSV",
                data=csv_buf.getvalue(),
                file_name=f"{invoice.invoice_number or 'invoice'}.csv",
                mime="text/csv",
            )

            # JSON Export
            json_str = json.dumps(invoice.model_dump(), indent=2)
            exp_col2.download_button(
                label="📥 Download JSON",
                data=json_str,
                file_name=f"{invoice.invoice_number or 'invoice'}.json",
                mime="application/json",
            )

            if show_ocr_raw:
                st.markdown("### Raw OCR Output")
                st.text_area("OCR Text", raw_text, height=250)

        except Exception as exc:
            st.error(f"Extraction failed: {exc}")
        finally:
            Path(tmp_path).unlink(missing_ok=True)
else:
    st.info("👆 Upload an invoice PDF or image above to see live OCR and structured extraction.")
