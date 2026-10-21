"""Combine NER spans and regex extraction into canonical field map."""

from __future__ import annotations

from typing import Any

from docextract.fields.extractors import extract_invoice
from docextract.ner.predict import extract_entities_with_fallback


def merge_ner_and_regex(text: str) -> dict[str, Any]:
    """Merge ML NER predictions with rule-based regex extractors."""
    # Run baseline regex extractor
    regex_res = extract_invoice(text)

    # Run NER model
    ner_res = extract_entities_with_fallback(text)

    merged = dict(regex_res)

    # If regex missed invoice number, check NER
    if (not merged.get("invoice_number") or merged["invoice_number"] == "UNKNOWN") and ner_res.get(
        "invoice_number_candidate"
    ):
        merged["invoice_number"] = ner_res["invoice_number_candidate"]

    # If regex missed vendor name, check NER
    if (
        not merged.get("vendor_name") or merged["vendor_name"] == "Unknown Vendor"
    ) and ner_res.get("vendor_candidate"):
        merged["vendor_name"] = ner_res["vendor_candidate"]

    return merged
