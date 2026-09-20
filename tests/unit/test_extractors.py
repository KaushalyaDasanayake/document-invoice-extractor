from docextract.fields.extractors import (
    extract_currency,
    extract_invoice,
    extract_invoice_number,
    extract_totals,
)
from docextract.fields.normalize import normalize_amount, normalize_date
from docextract.schemas.invoice import ExtractionResult


def test_normalize_date_formats():
    assert normalize_date("2026-08-10") == "2026-08-10"
    assert normalize_date("25/12/2026") == "2026-12-25"
    assert normalize_date("Aug 10, 2026") == "2026-08-10"
    assert normalize_date("invalid date") is None


def test_normalize_amount_formats():
    assert normalize_amount("$1,234.56") == 1234.56
    assert normalize_amount("1.234,56") == 1234.56
    assert normalize_amount("99.00") == 99.00
    assert normalize_amount("free") is None


def test_extract_invoice_number():
    text = "INVOICE #: INV-2026-0045\nDate: 2026-01-01"
    assert extract_invoice_number(text) == "INV-2026-0045"


def test_extract_currency():
    assert extract_currency("Total: EUR 50.00") == "EUR"
    assert extract_currency("Price: $25.00") == "USD"
    assert extract_currency("No currency here") == "USD"


def test_extract_totals():
    text = "Subtotal: $100.00\nTax: $10.00\nShipping: $5.00\nTotal: $115.00"
    totals = extract_totals(text)
    assert totals["subtotal"] == 100.0
    assert totals["tax"] == 10.0
    assert totals["shipping"] == 5.0
    assert totals["grand_total"] == 115.0


def test_extract_invoice_end_to_end_validates():
    sample = """
    Acme Industrial Supply
    123 Factory Lane, Detroit MI
    Invoice #: INV-2026-0045
    Date: 2026-03-01
    Due Date: 2026-03-31

    Bill To:
    Wayne Enterprises
    1007 Mountain Drive, Gotham

    Widgets Pro    5    10.00    50.00

    Subtotal: $50.00
    Tax: $5.00
    Grand Total: $55.00
    """
    raw_dict = extract_invoice(sample)
    result = ExtractionResult.model_validate(raw_dict)
    assert result.invoice_number == "INV-2026-0045"
    assert result.vendor_name == "Acme Industrial Supply"
    assert result.customer_name == "Wayne Enterprises"
    assert len(result.line_items) >= 1