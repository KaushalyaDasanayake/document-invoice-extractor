import html
import io
import json
import re
import sys
import tempfile
from pathlib import Path

# Add src to Python path so docextract package is discoverable
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
    page_title="Invoice Extractor | Enterprise Studio",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Enterprise B2B SaaS Styling (Stripe / Ramp aesthetic)
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    /* Global Typography */
    html, body, p, div, span, h1, h2, h3, h4, h5, h6, input, textarea, select {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    /* Preserve Streamlit icon font so ligature icons render as graphical icons instead of raw text */
    [data-testid="stIconMaterial"], .material-symbols-rounded, .material-symbols-outlined, .material-icons {
        font-family: 'Material Symbols Rounded', 'Material Icons' !important;
        font-weight: normal !important;
        font-style: normal !important;
    }

    /* Hide Streamlit default chrome & branding */
    #MainMenu { visibility: hidden !important; }
    header[data-testid="stHeader"] { display: none !important; }
    footer { display: none !important; }
    .viewerBadge_container__1QSob, [data-testid="stToolbar"] { display: none !important; }
    .stDeployButton { display: none !important; }

    /* Page container */
    .main .block-container {
        padding-top: 1.75rem !important;
        padding-bottom: 3.5rem !important;
        max-width: 1200px !important;
    }

    /* Modern SaaS Header */
    .app-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-bottom: 1.25rem;
        margin-bottom: 1.5rem;
        border-bottom: 1px solid #1e293b;
    }
    .header-left {
        display: flex;
        align-items: center;
        gap: 0.85rem;
    }
    .header-logo {
        width: 38px;
        height: 38px;
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #ffffff;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25);
    }
    .header-logo svg {
        width: 20px;
        height: 20px;
        stroke: #ffffff;
        stroke-width: 2;
        fill: none;
    }
    .app-title-group h1 {
        font-size: 1.35rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        color: #f8fafc !important;
        margin: 0 !important;
        padding: 0 !important;
        line-height: 1.2 !important;
    }
    .app-title-group p {
        font-size: 0.82rem !important;
        color: #94a3b8 !important;
        margin: 0 !important;
        padding-top: 2px !important;
    }
    .env-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        background: rgba(30, 41, 59, 0.8);
        border: 1px solid #334155;
        border-radius: 9999px;
        padding: 0.3rem 0.75rem;
        font-size: 0.74rem;
        font-weight: 600;
        color: #cbd5e1;
        letter-spacing: 0.02em;
    }
    .env-dot {
        width: 6px;
        height: 6px;
        background: #10b981;
        border-radius: 50%;
        box-shadow: 0 0 6px #10b981;
    }

    /* Sidebar container styling */
    [data-testid="stSidebar"] {
        background-color: #0b1120 !important;
        border-right: 1px solid #1e293b !important;
    }
    [data-testid="stSidebar"] .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
    }
    .sidebar-card {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 1.1rem;
        margin-bottom: 1.25rem;
    }
    .sidebar-heading {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #94a3b8;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }
    .pill-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        margin-top: 0.25rem;
    }
    .tech-pill {
        display: inline-flex;
        align-items: center;
        background: #1e293b;
        border: 1px solid #334155;
        color: #cbd5e1;
        padding: 0.25rem 0.55rem;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 500;
        letter-spacing: 0.01em;
    }

    /* Sleek File Uploader Dropzone */
    [data-testid="stFileUploader"] {
        margin-bottom: 1.5rem;
    }
    [data-testid="stFileUploader"] section {
        background-color: #0b1120 !important;
        border: 1.5px dashed #2b3245 !important;
        border-radius: 12px !important;
        padding: 1.5rem 1.25rem !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    [data-testid="stFileUploader"] section:hover {
        border-color: #3b82f6 !important;
        background-color: rgba(59, 130, 246, 0.03) !important;
    }
    [data-testid="stFileUploader"] button {
        background-color: #1e293b !important;
        color: #f1f5f9 !important;
        border: 1px solid #334155 !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        font-size: 0.84rem !important;
        padding: 0.45rem 1rem !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: none !important;
        transition: all 0.15s ease !important;
    }
    /* Ensure icon inside button displays cleanly alongside text */
    [data-testid="stFileUploader"] button [data-testid="stIconMaterial"] {
        font-family: 'Material Symbols Rounded', 'Material Icons' !important;
        font-size: 18px !important;
        margin-right: 0.35rem !important;
        display: inline-block !important;
    }
    [data-testid="stFileUploader"] button:hover {
        background-color: #2b3245 !important;
        border-color: #3b82f6 !important;
        color: #ffffff !important;
    }
    [data-testid="stFileUploader"] small {
        color: #64748b !important;
        font-size: 0.76rem !important;
        margin-top: 0.35rem !important;
    }

    /* Standardized Metric Cards */
    .metric-card {
        background: #0f172a;
        border: 1px solid #2b3245;
        border-radius: 10px;
        padding: 1rem 1.15rem;
        height: 88px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
    }
    .metric-card:hover {
        border-color: #3b82f6;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
        transform: translateY(-1px);
    }
    .metric-label {
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #94a3b8;
        margin-bottom: 0.35rem;
    }
    .metric-value {
        font-size: 1.18rem;
        font-weight: 700;
        color: #f8fafc;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .metric-value.accent {
        color: #38bdf8;
    }

    /* Party Cards */
    .party-card {
        background: #0f172a;
        border: 1px solid #2b3245;
        border-radius: 10px;
        padding: 1.15rem;
        height: 100%;
        min-height: 108px;
        transition: border-color 0.15s ease;
    }
    .party-card:hover {
        border-color: #384158;
    }
    .party-header {
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #38bdf8;
        margin-bottom: 0.35rem;
    }
    .party-name {
        font-size: 0.98rem;
        font-weight: 600;
        color: #f1f5f9;
        margin-bottom: 0.25rem;
    }
    .party-address {
        font-size: 0.8rem;
        color: #94a3b8;
        line-height: 1.45;
    }

    /* Polished Validation Notice */
    .validation-card {
        background: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.35);
        border-radius: 10px;
        padding: 0.85rem 1.15rem;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 0.85rem;
    }
    .validation-card.success {
        background: rgba(16, 185, 129, 0.08);
        border-color: rgba(16, 185, 129, 0.35);
    }
    .status-pill {
        display: inline-flex;
        align-items: center;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        padding: 0.25rem 0.65rem;
        border-radius: 6px;
        white-space: nowrap;
    }
    .status-pill.warn {
        background: rgba(245, 158, 11, 0.2);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.4);
    }
    .status-pill.ok {
        background: rgba(16, 185, 129, 0.2);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.4);
    }
    .validation-text {
        font-size: 0.84rem;
        color: #e2e8f0;
        line-height: 1.4;
    }

    /* Section Subheadings */
    .section-header {
        font-size: 0.92rem;
        font-weight: 700;
        letter-spacing: -0.01em;
        color: #f1f5f9;
        margin-top: 1.5rem;
        margin-bottom: 0.65rem;
        text-transform: uppercase;
        font-size: 0.76rem;
        letter-spacing: 0.06em;
        color: #94a3b8;
    }

    /* Dataframe table styling (Zebra striping & subtle border) */
    [data-testid="stDataFrame"] {
        border: 1px solid #2b3245 !important;
        border-radius: 10px !important;
        overflow: hidden !important;
    }

    /* Summary Totals Box */
    .totals-card {
        background: #0f172a;
        border: 1px solid #2b3245;
        border-radius: 10px;
        padding: 1.1rem 1.35rem;
        margin-top: 1rem;
        width: 340px;
        margin-left: auto;
    }
    .totals-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.84rem;
        color: #94a3b8;
        padding: 0.25rem 0;
    }
    .totals-row.grand {
        border-top: 1px solid #2b3245;
        margin-top: 0.45rem;
        padding-top: 0.65rem;
        font-size: 1.05rem;
        font-weight: 700;
        color: #f8fafc;
    }

    /* Custom button styling */
    .stDownloadButton button {
        background-color: #0f172a !important;
        color: #cbd5e1 !important;
        border: 1px solid #2b3245 !important;
        border-radius: 8px !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        padding: 0.45rem 1rem !important;
        transition: all 0.15s ease !important;
    }
    .stDownloadButton button:hover {
        background-color: #1e293b !important;
        border-color: #3b82f6 !important;
        color: #ffffff !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Enterprise Header
st.markdown(
    """
    <div class="app-header">
      <div class="header-left">
        <div class="header-logo">
          <svg viewBox="0 0 24 24">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="16" y1="13" x2="8" y2="13"></line>
            <line x1="16" y1="17" x2="8" y2="17"></line>
            <polyline points="10 9 9 9 8 9"></polyline>
          </svg>
        </div>
        <div class="app-title-group">
          <h1>Invoice Extractor Studio</h1>
          <p>Autonomous OCR, schema validation & financial export pipeline</p>
        </div>
      </div>
      <div class="env-badge">
        <span class="env-dot"></span>
        <span>PRODUCTION API v1.0</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar with Structured Cards & Tech Badges
with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-card">
            <div class="sidebar-heading">Privacy & Extraction Controls</div>
        """,
        unsafe_allow_html=True,
    )
    redact_pii = st.checkbox(
        "Redact Customer PII",
        value=False,
        help="Masks customer names and street addresses for GDPR/compliance.",
    )
    show_ocr_raw = st.checkbox(
        "View Raw Document Text",
        value=False,
        help="Inspect original unparsed text returned by Tesseract.",
    )
    show_confidences = st.checkbox(
        "Field Confidence Diagnostics",
        value=False,
        help="View token and regex match reliability score per field.",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class="sidebar-card">
            <div class="sidebar-heading">Engine Capabilities</div>
            <div class="pill-grid">
                <span class="tech-pill">Poppler PDF</span>
                <span class="tech-pill">Tesseract 5.3</span>
                <span class="tech-pill">Regex & NER</span>
                <span class="tech-pill">Pydantic v2</span>
                <span class="tech-pill">FastAPI</span>
                <span class="tech-pill">Cross-Field Math</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# File Uploader
uploaded_file = st.file_uploader(
    "Upload invoice PDF or scanned image",
    type=["pdf", "png", "jpg", "jpeg"],
    help="Accepts standard PDF, PNG, and JPG invoices up to 50MB.",
    label_visibility="collapsed",
)


def format_validation_warning(raw_warning: str, currency: str) -> str:
    """Format raw formula alert into clean human-readable copy."""
    # Pattern: Totals mismatch: subtotal(X) + tax(Y) + shipping(Z) = CALC, but grand_total is STATED
    match = re.search(
        r"subtotal\(([\d.]+)\)\s*\+\s*tax\(([\d.]+)\)\s*\+\s*shipping\(([\d.]+)\)\s*=\s*([\d.]+).*grand_total\s*is\s*([\d.]+)",
        raw_warning,
    )
    if match:
        _sub, _tax, _ship, calc_total, stated_total = match.groups()
        c_val = float(calc_total)
        s_val = float(stated_total)
        diff = s_val - c_val
        diff_str = f"+${abs(diff):.2f}" if diff > 0 else f"-${abs(diff):.2f}"
        return (
            f"Calculated total ({currency} {c_val:,.2f}) differs from stated "
            f"grand total ({currency} {s_val:,.2f}) by {diff_str}."
        )

    # Line items mismatch
    item_match = re.search(r"sum of items\(([\d.]+)\)\s*!=\s*subtotal\(([\d.]+)\)", raw_warning)
    if item_match:
        items_sum, sub = item_match.groups()
        return f"Line items sum ({currency} {float(items_sum):,.2f}) does not match stated subtotal ({currency} {float(sub):,.2f})."

    # Date anomaly
    if "precedes invoice_date" in raw_warning:
        return "Invoice due date is set earlier than the invoice issue date."

    return raw_warning


if uploaded_file is not None:
    suffix = Path(uploaded_file.name).suffix or ".bin"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    with st.spinner("Executing OCR engine and extracting structured fields..."):
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

            # Polished Validation Notice Card
            if warnings:
                clean_warnings = [
                    format_validation_warning(w, invoice.currency)
                    for w in warnings
                ]
                warn_body = " ".join(html.escape(w) for w in clean_warnings)
                st.markdown(
                    f"""
                    <div class="validation-card">
                        <span class="status-pill warn">Discrepancy Detected</span>
                        <span class="validation-text">{warn_body}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    """
                    <div class="validation-card success">
                        <span class="status-pill ok">Verified Contract</span>
                        <span class="validation-text">Mathematical balance verified: line items and taxes align with stated grand total.</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # 4 Standardized Metric Cards
            c1, c2, c3, c4 = st.columns(4)
            display_inv_date = invoice.invoice_date or "Not Detected"
            display_due_date = invoice.due_date or "Not Detected"

            with c1:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-label">Invoice Number</div>
                        <div class="metric-value">{html.escape(invoice.invoice_number)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with c2:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-label">Issue Date</div>
                        <div class="metric-value">{html.escape(display_inv_date)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with c3:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-label">Due Date</div>
                        <div class="metric-value">{html.escape(display_due_date)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with c4:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-label">Grand Total</div>
                        <div class="metric-value accent">{html.escape(invoice.currency)} {invoice.totals.grand_total:,.2f}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Party Cards (Vendor & Customer)
            st.markdown('<div class="section-header">Entity Identification</div>', unsafe_allow_html=True)
            p_col1, p_col2 = st.columns(2)
            with p_col1:
                st.markdown(
                    f"""
                    <div class="party-card">
                        <div class="party-header">Vendor / Originator</div>
                        <div class="party-name">{html.escape(invoice.vendor_name)}</div>
                        <div class="party-address">{html.escape(invoice.vendor_address or 'No billing address detected')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with p_col2:
                st.markdown(
                    f"""
                    <div class="party-card">
                        <div class="party-header">Client / Recipient</div>
                        <div class="party-name">{html.escape(invoice.customer_name)}</div>
                        <div class="party-address">{html.escape(invoice.customer_address or 'No billing address detected')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Line Items Table
            st.markdown('<div class="section-header">Itemized Line Items</div>', unsafe_allow_html=True)

            items_records = [
                {
                    "Description": item.description,
                    "Qty": float(item.quantity),
                    "Unit Price": float(item.unit_price),
                    "Line Total": float(item.line_total),
                }
                for item in invoice.line_items
            ]
            df_items = pd.DataFrame(items_records)

            st.dataframe(
                df_items,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Description": st.column_config.TextColumn(
                        "Description",
                        width="large",
                        alignment="left",
                    ),
                    "Qty": st.column_config.NumberColumn(
                        "Qty",
                        format="%.0f",
                        alignment="right",
                        width="small",
                    ),
                    "Unit Price": st.column_config.NumberColumn(
                        f"Unit Price ({invoice.currency})",
                        format=f"{invoice.currency} %.2f",
                        alignment="right",
                        width="medium",
                    ),
                    "Line Total": st.column_config.NumberColumn(
                        f"Line Total ({invoice.currency})",
                        format=f"{invoice.currency} %.2f",
                        alignment="right",
                        width="medium",
                    ),
                },
            )

            # Summary Totals Box
            st.markdown(
                f"""
                <div class="totals-card">
                    <div class="totals-row">
                        <span>Subtotal:</span>
                        <span>{html.escape(invoice.currency)} {invoice.totals.subtotal:,.2f}</span>
                    </div>
                    <div class="totals-row">
                        <span>Tax:</span>
                        <span>{html.escape(invoice.currency)} {invoice.totals.tax:,.2f}</span>
                    </div>
                    <div class="totals-row">
                        <span>Shipping:</span>
                        <span>{html.escape(invoice.currency)} {invoice.totals.shipping:,.2f}</span>
                    </div>
                    <div class="totals-row grand">
                        <span>Grand Total:</span>
                        <span>{html.escape(invoice.currency)} {invoice.totals.grand_total:,.2f}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Export Bar
            st.markdown('<div class="section-header">Export Document Data</div>', unsafe_allow_html=True)
            e1, e2, _ = st.columns([1, 1, 3])

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

            with e1:
                st.download_button(
                    label="Export CSV",
                    data=csv_buf.getvalue(),
                    file_name=f"{invoice.invoice_number or 'invoice'}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

            with e2:
                json_data = json.dumps(invoice.model_dump(), indent=2)
                st.download_button(
                    label="Export JSON",
                    data=json_data,
                    file_name=f"{invoice.invoice_number or 'invoice'}.json",
                    mime="application/json",
                    use_container_width=True,
                )

            # Diagnostics Drawer
            if show_confidences:
                st.markdown('<div class="section-header">Field Confidence Scores</div>', unsafe_allow_html=True)
                conf_df = pd.DataFrame([
                    {"Field": k, "Confidence Score": f"{v * 100:.1f}%"}
                    for k, v in confidences.items()
                ])
                st.dataframe(conf_df, hide_index=True, use_container_width=False)

            if show_ocr_raw:
                st.markdown('<div class="section-header">Raw OCR Inspection</div>', unsafe_allow_html=True)
                st.text_area("Extracted OCR Text", raw_text, height=200, label_visibility="collapsed")

        except Exception as exc:
            st.error(f"Extraction error: {exc}")
        finally:
            Path(tmp_path).unlink(missing_ok=True)
else:
    st.info("Upload an invoice document above to view automated extraction.")
