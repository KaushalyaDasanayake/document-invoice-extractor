"""Cross-field validation and confidence scoring for extracted invoices."""

from __future__ import annotations

from typing import Any


def calculate_field_confidences(invoice_data: dict[str, Any]) -> dict[str, float]:
    """Compute confidence scores [0.0, 1.0] for extracted fields based on presence and format."""
    confidences: dict[str, float] = {}

    # Invoice number
    inv_num = invoice_data.get("invoice_number", "")
    if inv_num and inv_num != "UNKNOWN":
        confidences["invoice_number"] = 0.95
    else:
        confidences["invoice_number"] = 0.2

    # Dates
    inv_date = invoice_data.get("invoice_date", "")
    confidences["invoice_date"] = 0.95 if inv_date and inv_date != "1970-01-01" else 0.2

    due_date = invoice_data.get("due_date", "")
    confidences["due_date"] = 0.90 if due_date and due_date != "1970-01-01" else 0.2

    # Parties
    v_name = invoice_data.get("vendor_name", "")
    confidences["vendor_name"] = 0.90 if v_name and v_name != "Unknown Vendor" else 0.3

    c_name = invoice_data.get("customer_name", "")
    confidences["customer_name"] = 0.90 if c_name and c_name != "Unknown Customer" else 0.3

    # Totals
    totals = invoice_data.get("totals", {})
    subtotal = totals.get("subtotal", 0.0)
    grand_total = totals.get("grand_total", 0.0)
    confidences["totals"] = 0.95 if subtotal > 0 and grand_total > 0 else 0.5

    # Line items
    line_items = invoice_data.get("line_items", [])
    if line_items and line_items[0].get("description") != "Invoice Items":
        confidences["line_items"] = 0.85
    else:
        confidences["line_items"] = 0.40

    return confidences


def validate_cross_fields(invoice_data: dict[str, Any]) -> list[str]:
    """Run mathematical and logical consistency checks on extracted fields."""
    warnings: list[str] = []

    totals = invoice_data.get("totals", {})
    subtotal = totals.get("subtotal", 0.0)
    tax = totals.get("tax", 0.0)
    shipping = totals.get("shipping", 0.0)
    grand_total = totals.get("grand_total", 0.0)

    # Cross check 1: totals arithmetic: subtotal + tax + shipping ~= grand_total
    expected_grand = round(subtotal + tax + shipping, 2)
    if grand_total > 0 and abs(expected_grand - grand_total) > 0.05:
        warnings.append(
            f"Totals mismatch: subtotal({subtotal}) + tax({tax}) + shipping({shipping}) "
            f"= {expected_grand}, but grand_total is {grand_total}"
        )

    # Cross check 2: sum of line items should match subtotal
    line_items = invoice_data.get("line_items", [])
    if line_items and line_items[0].get("description") != "Invoice Items":
        sum_lines = round(sum(item.get("line_total", 0.0) for item in line_items), 2)
        if subtotal > 0 and abs(sum_lines - subtotal) > 0.05:
            warnings.append(
                f"Line items total mismatch: sum of items({sum_lines}) != subtotal({subtotal})"
            )

    # Cross check 3: due date should not be before invoice date
    inv_date = invoice_data.get("invoice_date")
    due_date = invoice_data.get("due_date")
    if inv_date and due_date and inv_date != "1970-01-01" and due_date != "1970-01-01":
        if due_date < inv_date:
            warnings.append(
                f"Date anomaly: due_date({due_date}) precedes invoice_date({inv_date})"
            )

    return warnings
