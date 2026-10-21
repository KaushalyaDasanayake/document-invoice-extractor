from docextract.postprocess.redact import redact_invoice_data
from docextract.postprocess.validate import (
    calculate_field_confidences,
    validate_cross_fields,
)


def test_confidence_scoring():
    sample = {
        "invoice_number": "INV-100",
        "invoice_date": "2026-05-01",
        "due_date": "2026-05-15",
        "vendor_name": "Acme Corp",
        "customer_name": "John Doe",
        "totals": {"subtotal": 100.0, "grand_total": 100.0},
        "line_items": [{"description": "Item 1", "quantity": 1, "unit_price": 100.0, "line_total": 100.0}],
    }
    confs = calculate_field_confidences(sample)
    assert confs["invoice_number"] >= 0.9
    assert confs["invoice_date"] >= 0.9
    assert confs["totals"] >= 0.9


def test_cross_field_validation_warnings():
    # Inconsistent totals: subtotal 100 + tax 10 != grand total 150
    sample = {
        "invoice_number": "INV-100",
        "invoice_date": "2026-05-20",
        "due_date": "2026-05-10",  # due date before invoice date!
        "totals": {"subtotal": 100.0, "tax": 10.0, "shipping": 0.0, "grand_total": 150.0},
        "line_items": [{"description": "Item 1", "line_total": 90.0}],
    }
    warnings = validate_cross_fields(sample)
    assert any("Totals mismatch" in w for w in warnings)
    assert any("Line items total mismatch" in w for w in warnings)
    assert any("Date anomaly" in w for w in warnings)


def test_pii_redaction():
    sample = {
        "vendor_name": "Acme Corp",
        "customer_name": "Wayne Enterprises",
        "customer_address": "1007 Mountain Drive",
        "payment": {"account_number": "123456789012"},
    }
    redacted = redact_invoice_data(sample)
    assert redacted["vendor_name"] == "Acme Corp"  # Vendor stays unredacted
    assert "Wayne Enterprises" not in redacted["customer_name"]
    assert redacted["customer_address"] == "[REDACTED ADDRESS]"
    assert redacted["payment"]["account_number"] == "XXXX-XXXX-9012"
