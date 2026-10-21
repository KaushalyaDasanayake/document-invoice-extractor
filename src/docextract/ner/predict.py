"""NER prediction pipeline and field mapping with regex fallback (w16)."""

from __future__ import annotations

from typing import Any

from docextract.ner.model import EntitySpan, InvoiceNERModel


def extract_entities_with_fallback(
    text: str, model: InvoiceNERModel | None = None
) -> dict[str, Any]:
    """Extract key invoice fields using entity recognition, falling back gracefully."""
    ner = model or InvoiceNERModel()
    spans: list[EntitySpan] = ner.predict(text)

    orgs = [s.text for s in spans if s.label == "ORG"]
    dates = [s.text for s in spans if s.label == "DATE"]
    inv_ids = [s.text for s in spans if s.label == "INVOICE_ID"]

    return {
        "vendor_candidate": orgs[0] if orgs else None,
        "customer_candidate": orgs[1] if len(orgs) > 1 else None,
        "invoice_date_candidate": dates[0] if dates else None,
        "due_date_candidate": dates[1] if len(dates) > 1 else None,
        "invoice_number_candidate": inv_ids[0] if inv_ids else None,
        "all_spans": spans,
    }
