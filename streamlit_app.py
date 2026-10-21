import html
import io
import json
import os
import sys
import tempfile
from pathlib import Path

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
    page_title="Invoice Data Extractor Studio",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom enterprise CSS styling
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }

    /* Header styling */
    .app-header {
        margin-bottom: 1.75rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
    .app-title {
        font-size: 1.65rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin-bottom: 0.25rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .app-subtitle {
        color: #94a3b8;
        font-size: 0.88rem;
        font-weight: 400;
    }

    /* Key-value summary cards */
    .stat-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 0.85rem 1rem;
        margin-bottom: 0.75rem;
    }
    .stat-label {
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #94a3b8;
        margin-bottom: 0.2rem;
    }
    .stat-value {
        font-size: 1.15rem;
        font-weight: 600;
        color: #f8fafc;
    }

    /* Party info cards */
    .party-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 1rem;
        height: 100%;
    }
    .party-title {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #38bdf8;
        margin-bottom: 0.4rem;
    }
    .party-name {
        font-size: 1rem;
        font-weight: 600;
        color: #f1f5f9;
        margin-bottom: 0.25rem;
    }
    .party-address {
        font-size: 0.82rem;
        color: #94a3b8;
        line-height: 1.4;
    }

    /* Totals box */
    .totals-wrapper {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 1rem 1.25rem;
        margin-top: 1rem;
        max-width: 360px;
        margin-left: auto;
    }
    .totals-line {
        display: flex;
        justify-content: space-between;
        font-size: 0.85rem;
        color: #94a3b8;
        padding: 0.25rem 0;
    }
    .totals-line.grand {
        border-top: 1px solid #334155;
        margin-top: 0.4rem;
        padding-top: 0.5rem;
        font-size: 1.05rem;
        font-weight: 700;
        color: #f8fafc;
    }

    /* Validation notice */
    .validation-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.45rem 0.85rem;
        border-radius: 6px;
        font-size: 0.82rem;
        font-weight: 500;
        margin-bottom: 1.25rem;
    }
    .validation-ok {
        background: rgba(16, 185, 129, 0.12);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .validation-warn {
        background: rgba(245, 158, 11, 0.12);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }

    /* Section headers */
    .section-title {
        font-size: 0.95rem;
        font-weight: 600;
        letter-spacing: -0.01em;
        color: #e2e8f0;
        margin-top: 1.25rem;
        margin-bottom: 0.6rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Header
st.markdown(
    """
    <div class="app-header">
      <div class="app-title">🧾 Invoice Data Extractor Studio</div>
      <div class="app-subtitle">Automated OCR, structured entity parsing, cross-field validation, and multi-format export</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar
with st.sidebar:
    st.markdown("### Configuration")
    redact_pii = st.checkbox("Redact Customer PII", value=False, help="Masks customer names and address for GDPR/privacy compliance.")
    show_ocr_raw = st.checkbox("View Raw OCR Text", value=False)
    show_confidences = st.checkbox("Show Field Confidences", value=False)

    st.markdown("---")
    st.markdown(
        """
        <div style="font-size: 0.8rem; color: #94a3b8; line-height: 1.5;">
        <strong style="color: #cbd5e1;">Capabilities</strong><br>
        • PDF rasterization (Poppler)<br>
        • Tesseract OCR engine<br>
        • Heuristic NER & Regex parsers<br>
        • Arithmetic cross-field checks<br>
        • Pydantic v2 contract enforcement
        </div>
        """,
        unsafe_allow_html=True,
    )

uploaded_file = st.file_uploader(
    "Choose an invoice file",
    type=["pdf", "png", "jpg", "jpeg"],
    help="Upload scanned or digital invoices in PDF, PNG, or JPG formats.",
)

if uploaded_file is not None:
    suffix = Path(uploaded_file.name).suffix or ".bin"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    with st.spinner("Extracting and validating invoice data..."):
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

            # Validation Status
            if warnings:
                warn_msg = " | ".join(html.escape(w) for w in warnings)
                st.markdown(
                    f'<div class="validation-badge validation-warn">⚠️ {warn_msg}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="validation-badge validation-ok">✓ Mathematical and contract checks verified</div>',
                    unsafe_allow_html=True,
                )

            # 4 Metric Cards
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(
                    f"""
                    <div class="stat-card">
                        <div class="stat-label">Invoice Number</div>
                        <div class="stat-value">{html.escape(invoice.invoice_number)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with c2:
                st.markdown(
                    f"""
                    <div class="stat-card">
                        <div class="stat-label">Issue Date</div>
                        <div class="stat-value">{html.escape(invoice.invoice_date)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with c3:
                st.markdown(
                    f"""
                    <div class="stat-card">
                        <div class="stat-label">Due Date</div>
                        <div class="stat-value">{html.escape(invoice.due_date)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with c4:
                st.markdown(
                    f"""
                    <div class="stat-card">
                        <div class="stat-label">Grand Total</div>
                        <div class="stat-value" style="color: #38bdf8;">{html.escape(invoice.currency)} {invoice.totals.grand_total:,.2f}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Parties: Vendor & Customer
            p_col1, p_col2 = st.columns(2)
            with p_col1:
                st.markdown(
                    f"""
                    <div class="party-card">
                        <div class="party-title">Vendor / Seller</div>
                        <div class="party-name">{html.escape(invoice.vendor_name)}</div>
                        <div class="party-address">{html.escape(invoice.vendor_address or 'No address detected')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with p_col2:
                st.markdown(
                    f"""
                    <div class="party-card">
                        <div class="party-title">Bill To / Customer</div>
                        <div class="party-name">{html.escape(invoice.customer_name)}</div>
                        <div class="party-address">{html.escape(invoice.customer_address or 'No address detected')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Line Items Table
            st.markdown('<div class="section-title">Itemized Line Items</div>', unsafe_allow_html=True)

            items_records = []
            for item in invoice.line_items:
                items_records.append({
                    "Description": item.description,
                    "Qty": int(item.quantity) if item.quantity.is_integer() else item.quantity,
                    f"Unit Price ({invoice.currency})": f"{item.unit_price:,.2f}",
                    f"Line Total ({invoice.currency})": f"{item.line_total:,.2f}",
                })

            df_items = pd.DataFrame(items_records)
            st.dataframe(
                df_items,
                use_container_width=True,
                hide_index=True,
            )

            # Totals breakdown card
            st.markdown(
                f"""
                <div class="totals-wrapper">
                    <div class="totals-line"><span>Subtotal:</span><span>{html.escape(invoice.currency)} {invoice.totals.subtotal:,.2f}</span></div>
                    <div class="totals-line"><span>Tax:</span><span>{html.escape(invoice.currency)} {invoice.totals.tax:,.2f}</span></div>
                    <div class="totals-line"><span>Shipping:</span><span>{html.escape(invoice.currency)} {invoice.totals.shipping:,.2f}</span></div>
                    <div class="totals-line grand"><span>Grand Total:</span><span>{html.escape(invoice.currency)} {invoice.totals.grand_total:,.2f}</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Export Options
            st.markdown('<div class="section-title">Export Extraction</div>', unsafe_allow_html=True)
            e_col1, e_col2, _ = st.columns([1, 1, 3])

            # Prepare CSV
            csv_buf = io.StringIO()
            csv_buf.write(f"Invoice Number,{invoice.invoice_number}\n")
            csv_buf.write(f"Vendor,{invoice.vendor_name}\n")
            csv_buf.write(f"Customer,{invoice.customer_name}\n")
            csv_buf.write(f"Issue Date,{invoice.invoice_date}\n")
            csv_buf.write(f"Due Date,{invoice.due_date}\n")
            csv_buf.write(f"Currency,{invoice.currency}\n\n")

            export_df = pd.DataFrame([
                {
                    "Description": it.description,
                    "Quantity": it.quantity,
                    "UnitPrice": it.unit_price,
                    "LineTotal": it.line_total,
                }
                for it in invoice.line_items
            ])
            export_df.to_csv(csv_buf, index=False)

            csv_buf.write(f"\nSubtotal,{invoice.totals.subtotal}\n")
            csv_buf.write(f"Tax,{invoice.totals.tax}\n")
            csv_buf.write(f"Shipping,{invoice.totals.shipping}\n")
            csv_buf.write(f"Grand Total,{invoice.totals.grand_total}\n")

            with e_col1:
                st.download_button(
                    label="Export CSV",
                    data=csv_buf.getvalue(),
                    file_name=f"{invoice.invoice_number or 'invoice'}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

            with e_col2:
                json_data = json.dumps(invoice.model_dump(), indent=2)
                st.download_button(
                    label="Export JSON",
                    data=json_data,
                    file_name=f"{invoice.invoice_number or 'invoice'}.json",
                    mime="application/json",
                    use_container_width=True,
                )

            # Optional Diagnostics
            if show_confidences:
                st.markdown('<div class="section-title">Field Confidence Diagnostics</div>', unsafe_allow_html=True)
                conf_df = pd.DataFrame([
                    {"Field": k, "Confidence Score": f"{v * 100:.1f}%"}
                    for k, v in confidences.items()
                ])
                st.dataframe(conf_df, hide_index=True, use_container_width=False)

            if show_ocr_raw:
                st.markdown('<div class="section-title">Raw Document Text (OCR)</div>', unsafe_allow_html=True)
                st.text_area("Extracted Text", raw_text, height=200, label_visibility="collapsed")

        except Exception as exc:
            st.error(f"Extraction error: {exc}")
        finally:
            Path(tmp_path).unlink(missing_ok=True)
else:
    st.info("Upload an invoice document above to view extraction results.")
