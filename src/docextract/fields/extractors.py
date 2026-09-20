from __future__ import annotations

import re

from docextract.fields.normalize import normalize_amount, normalize_date

CURRENCY_MAP = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP"
}


def extract_invoice_number(text: str) -> str | None:
    """Find and return invoice number identifier."""
    pattern = r"(?i)\b(?:invoice|inv)[\s#.:-]*([A-Z0-9-]{3,})\b"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None


def extract_currency(text: str) -> str:
    """Detect currency ISO code, defaulting to USD"""
    # check 3 letter codes
    code_match = re.search(r"\b(USD|EUR|GBP|CAD|AUD)\b", text)
    if code_match:
        return code_match.group(1).upper()

    # symbols
    symbol_match = re.search(r"([$€£])", text)
    if symbol_match:
        return CURRENCY_MAP.get(symbol_match.group(1), "USD")

    return "USD"


def extract_date_field(text: str, label_pattern: str) -> str | None:
    """Extract a date with a specific label prefix"""
    # look for label followed by date-like tokens
    pattern =  rf"(?i){label_pattern}[\s#.:-]*([A-Za-z0-9/,\s-]{{6,20}})"
    match = re.search(pattern, text)
    if match:
        raw_val = match.group(1).strip()
        # take first line if OCR ran multiple lines together
        first_line = raw_val.split("\n")[0].strip()
        return normalize_date(first_line)
    return None


def extract_invoice_date(text: str) -> str | None:
    """Extract the invoice issue date."""
    return extract_date_field(
        text, r"(?:invoice\s*date|date\s*of\s*issue|issue\s*date|\bdate\b|dated)"
    )

def extract_due_date(text: str) -> str | None:
    """Extract the invoice payement due date."""
    return extract_date_field(text, r"(?:due\s*date|payment\s*due|pay\s*by)")


def extract_amount_field(text: str, label_pattern: str) -> float | None:
    """Find a money amount following a specific label on the same line."""
    # Matches: label, optional colon/dashes/spaces, optional currency symbol, number with optional cents
    pattern = rf"(?im)^\s*{label_pattern}[^\n\d]*?([$€£]?\s*\d[\d,.]*)"
    match = re.search(pattern, text)
    if match:
        val = normalize_amount(match.group(1))
        return val
    return None


def extract_totals(text: str) -> dict[str, float]:
    """Extract subtotal, tax, shipping, and grand_total."""
    subtotal = extract_amount_field(
        text, r"(?:sub\s*total|subtotal|net\s*amount)"
    )
    tax = extract_amount_field(
        text, r"(?:tax|vat|gst)"
    ) or 0.0
    shipping = extract_amount_field(
        text, r"(?:shipping|freight|delivery)"
    ) or 0.0
    grand_total = extract_amount_field(
        text, r"(?:grand\s*total|total\s*due|balance\s*due|amount\s*due)"
    )
    if grand_total is None:
        grand_total = extract_amount_field(text, r"total")

    # If subtotal is missing but grand_total exists
    if subtotal is None and grand_total is not None:
        subtotal = round(grand_total - tax - shipping, 2)

    # If grand_total is missing but subtotal exists
    if grand_total is None and subtotal is not None:
        grand_total = round(subtotal + tax + shipping, 2)

    return {
        "subtotal": subtotal or 0.0,
        "tax": tax,
        "shipping": shipping,
        "grand_total": grand_total or 0.0,
    }


def extract_parties(text: str) -> dict[str, str]:
    """Extract vendor and customer name/address blocks"""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    # Vendor is typically in the first 1-3 lines of header
    vendor_name = lines[0] if lines else "Unknown Vendor"
    vendor_address = lines[1] if len(lines) > 1 else ""

    customer_name = "Unknown Customer"
    customer_address = ""

    # look for bill to / invoice to pattern
    bill_to_match = re.search(
        r"(?i)(?:bill\s*to|invoice\s*to|sold\s*to)[:\s]*\n?([^\n]+)(?:\n([^\n]+))?",
        text,
    )
    if bill_to_match:
        customer_name = bill_to_match.group(1).strip()
        if bill_to_match.group(2):
            customer_address = bill_to_match.group(2).strip()

    return {
        "vendor_name": vendor_name,
        "vendor_address": vendor_address,
        "customer_name": customer_name,
        "customer_address": customer_address,
    }


def extract_line_items(text: str, totals: dict[str, float]) -> list[dict]:
    """Extract item rows or construct fallback line item matching totals."""
    # pattern matching lines like: "widget A   2   50.00   100.00"
    item_pattern = (
        r"(?m)^([A-Za-z0-9.,#&'-]+(?:[^\S\r\n]+[A-Za-z0-9.,#&'-]+)*)"
        r"[^\S\r\n]+(\d+(?:\.\d+)?)"
        r"[^\S\r\n]+([$€£]?\s*\d+\.\d{2})"
        r"[^\S\r\n]+([$€£]?\s*\d+\.\d{2})$"
    )
    items = []

    for match in re.finditer(item_pattern, text):
        desc, qty, unit, total = match.groups()
        # avoid capturing header lines
        if any(w in desc.lower() for w in ["subtotal", "tax", "total", "description", "qty"]):
            continue
        try:
            qty_f = float(qty)
            unit_f = normalize_amount(unit)
            total_f = normalize_amount(total)
            if qty_f > 0 and unit_f and total_f:
                items.append({
                    "description": desc.strip(),
                    "quantity": qty_f,
                    "unit_price": unit_f,
                    "line_total": total_f,
                })
        except ValueError:
            continue

    # fallback to satisfy schema requirement (min_length=1)
    if not items:
        amount = totals["subtotal"] if totals["subtotal"] > 0 else totals["grand_total"]
        items.append({
            "description": "Invoice Items",
            "quantity": 1.0,
            "unit_price": max(amount, 0.01),
            "line_total": max(amount, 0.01),
        })

    return items


def extract_invoice(text: str) -> dict:
    """run full regex extraction pipeline and return dict ready for ExtractionResult."""
    parties = extract_parties(text)
    totals = extract_totals(text)
    inv_date = extract_invoice_date(text) or "1970-01-01"
    due_date = extract_due_date(text) or inv_date

    return {
        "vendor_name": parties["vendor_name"],
        "vendor_address": parties["vendor_address"],
        "customer_name": parties["customer_name"],
        "customer_address": parties["customer_address"],
        "invoice_number": extract_invoice_number(text) or "UNKNOWN",
        "invoice_date": inv_date,
        "due_date": due_date,
        "currency": extract_currency(text),
        "totals": totals,
        "line_items": extract_line_items(text, totals),
    }