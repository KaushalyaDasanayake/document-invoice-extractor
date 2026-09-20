from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
INPUTS_DIR = ROOT / "golden_set" / "inputs"
EXPECTED_DIR = ROOT / "golden_set" / "expected"
AGGREGATE_JSON = ROOT / "golden_set" / "invoices_v1.json"
SESSIONS_JSON = ROOT / "golden_set" / "sessions.json"

PAGE_WIDTH = 1240
PAGE_HEIGHT = 1754
MARGIN_X = 90
MARGIN_Y = 80
ROW_HEIGHT = 44

TEMPLATES = {
    "classic_blue": {
        "accent": "#1F4E79",
        "muted": "#5B6572",
        "table_fill": "#EAF2F8",
        "max_rows": 18,
    },
    "minimal_green": {
        "accent": "#2E6F40",
        "muted": "#4A5C4F",
        "table_fill": "#EEF7F0",
        "max_rows": 15,
    },
    "bold_orange": {
        "accent": "#B85C00",
        "muted": "#6C584C",
        "table_fill": "#FFF1E5",
        "max_rows": 12,
    },
}


def sample_invoices() -> list[dict[str, Any]]:
    invoices = [
        {
            "sample_id": "invoice_001",
            "template": "classic_blue",
            "vendor": {
                "name": "Northwind Office Supplies Ltd",
                "address": "145 Lakeview Avenue, Seattle, WA 98101, USA",
                "phone": "+1-206-555-0147",
                "email": "billing@northwind-office.test",
            },
            "customer": {
                "name": "BluePeak Analytics",
                "address": "22 Market Street, San Francisco, CA 94105, USA",
            },
            "invoice": {
                "invoice_number": "NWO-2026-0001",
                "invoice_date": "2026-08-10",
                "due_date": "2026-08-25",
                "currency": "USD",
            },
            "line_items": [
                {"description": "A4 Copy Paper Box", "quantity": 10, "unit_price": 24.50, "line_total": 245.00},
                {"description": "Black Toner Cartridge", "quantity": 3, "unit_price": 89.99, "line_total": 269.97},
                {"description": "Desk Organizer Set", "quantity": 5, "unit_price": 18.00, "line_total": 90.00},
            ],
            "totals": {"subtotal": 604.97, "tax": 48.40, "shipping": 15.00, "grand_total": 668.37},
            "payment": {
                "bank_name": "Demo Commercial Bank",
                "account_name": "Northwind Office Supplies Ltd",
                "account_number": "XXXX-XXXX-1024",
            },
            "notes": "Thank you for your business.",
        },
        {
            "sample_id": "invoice_002",
            "template": "minimal_green",
            "vendor": {
                "name": "GreenField Industrial Parts Co",
                "address": "88 Foundry Road, Columbus, OH 43215, USA",
                "phone": "+1-614-555-0182",
                "email": "accounts@greenfield-parts.test",
            },
            "customer": {
                "name": "Vertex Mechanical Services",
                "address": "410 River Park Drive, Pittsburgh, PA 15222, USA",
            },
            "invoice": {
                "invoice_number": "GFI-2026-1042",
                "invoice_date": "2026-07-29",
                "due_date": "2026-08-28",
                "currency": "USD",
            },
            "line_items": [
                {"description": "Hydraulic Valve Assembly", "quantity": 4, "unit_price": 135.50, "line_total": 542.00},
                {"description": "Steel Mounting Bracket", "quantity": 20, "unit_price": 12.75, "line_total": 255.00},
                {"description": "Pressure Gauge 0-300 PSI", "quantity": 6, "unit_price": 48.20, "line_total": 289.20},
            ],
            "totals": {"subtotal": 1086.20, "tax": 86.90, "shipping": 24.50, "grand_total": 1197.60},
            "payment": {
                "bank_name": "Midwest Trade Bank",
                "account_name": "GreenField Industrial Parts Co",
                "account_number": "XXXX-XXXX-3318",
            },
            "notes": "Net 30 payment terms apply.",
        },
        {
            "sample_id": "invoice_003",
            "template": "bold_orange",
            "vendor": {
                "name": "Luna Creative Studio",
                "address": "17 King Street West, Toronto, ON M5H 1A1, Canada",
                "phone": "+1-416-555-0114",
                "email": "finance@luna-creative.test",
            },
            "customer": {
                "name": "Harbor Retail Group",
                "address": "250 Granville Street, Vancouver, BC V6C 1S4, Canada",
            },
            "invoice": {
                "invoice_number": "LCS-2026-087",
                "invoice_date": "2026-08-02",
                "due_date": "2026-08-16",
                "currency": "CAD",
            },
            "line_items": [
                {"description": "Brand Identity Refresh", "quantity": 1, "unit_price": 2200.00, "line_total": 2200.00},
                {"description": "Social Media Asset Pack", "quantity": 2, "unit_price": 480.00, "line_total": 960.00},
                {"description": "Print Flyer Design", "quantity": 3, "unit_price": 150.00, "line_total": 450.00},
            ],
            "totals": {"subtotal": 3610.00, "tax": 469.30, "shipping": 0.00, "grand_total": 4079.30},
            "payment": {
                "bank_name": "Northern Maple Bank",
                "account_name": "Luna Creative Studio",
                "account_number": "XXXX-XXXX-7782",
            },
            "notes": "Please include invoice number in the transfer reference.",
        },
        {
            "sample_id": "invoice_004",
            "template": "classic_blue",
            "vendor": {
                "name": "Bergmann Elektronik GmbH",
                "address": "Kaiserstrasse 44, 60311 Frankfurt am Main, Germany",
                "phone": "+49-69-555-2041",
                "email": "rechnung@bergmann-elektronik.test",
            },
            "customer": {
                "name": "Nordic Automation AS",
                "address": "Dronning Eufemias gate 16, 0191 Oslo, Norway",
            },
            "invoice": {
                "invoice_number": "BEG-2026-5519",
                "invoice_date": "2026-06-18",
                "due_date": "2026-07-18",
                "currency": "EUR",
            },
            "line_items": [
                {"description": "Industrial Sensor Module", "quantity": 12, "unit_price": 84.50, "line_total": 1014.00},
                {"description": "Control Relay Unit", "quantity": 8, "unit_price": 126.75, "line_total": 1014.00},
                {"description": "Installation Kit", "quantity": 5, "unit_price": 39.90, "line_total": 199.50},
            ],
            "totals": {"subtotal": 2227.50, "tax": 423.23, "shipping": 35.00, "grand_total": 2685.73},
            "payment": {
                "bank_name": "Rhein Main Handelsbank",
                "account_name": "Bergmann Elektronik GmbH",
                "account_number": "DE89 XXXX XXXX 5520",
            },
            "notes": "Payment due within 30 days.",
        },
        {
            "sample_id": "invoice_005",
            "template": "minimal_green",
            "vendor": {
                "name": "Sakura Medical Consumables KK",
                "address": "2-14-7 Nihonbashi, Chuo-ku, Tokyo 103-0027, Japan",
                "phone": "+81-3-5550-1821",
                "email": "billing@sakura-medical.test",
            },
            "customer": {
                "name": "Pacific Care Hospital",
                "address": "85 Orchard Boulevard, Singapore 238880, Singapore",
            },
            "invoice": {
                "invoice_number": "SMC-2026-2304",
                "invoice_date": "2026-08-05",
                "due_date": "2026-09-04",
                "currency": "JPY",
            },
            "line_items": [
                {"description": "Disposable Examination Gloves", "quantity": 50, "unit_price": 1200, "line_total": 60000},
                {"description": "Sterile Syringe Pack", "quantity": 30, "unit_price": 1850, "line_total": 55500},
                {"description": "Surgical Mask Carton", "quantity": 40, "unit_price": 980, "line_total": 39200},
            ],
            "totals": {"subtotal": 154700, "tax": 15470, "shipping": 3200, "grand_total": 173370},
            "payment": {
                "bank_name": "Tokyo Central Trust",
                "account_name": "Sakura Medical Consumables KK",
                "account_number": "XXXX-2194",
            },
            "notes": "Hospital procurement order PO-88421 referenced.",
        },
        {
            "sample_id": "invoice_006",
            "template": "bold_orange",
            "vendor": {
                "name": "Cape Horizon Logistics Pty Ltd",
                "address": "41 Dockyard Lane, Cape Town 8001, South Africa",
                "phone": "+27-21-555-0199",
                "email": "invoices@capehorizon-logistics.test",
            },
            "customer": {
                "name": "SunGrid Energy Solutions",
                "address": "12 Independence Avenue, Windhoek, Namibia",
            },
            "invoice": {
                "invoice_number": "CHL-2026-390",
                "invoice_date": "2026-07-12",
                "due_date": "2026-07-26",
                "currency": "ZAR",
            },
            "line_items": [
                {"description": "Cross-border Freight Service", "quantity": 1, "unit_price": 18500.00, "line_total": 18500.00},
                {"description": "Warehouse Handling Fee", "quantity": 3, "unit_price": 1450.00, "line_total": 4350.00},
                {"description": "Customs Documentation", "quantity": 2, "unit_price": 950.00, "line_total": 1900.00},
            ],
            "totals": {"subtotal": 24750.00, "tax": 3712.50, "shipping": 0.00, "grand_total": 28462.50},
            "payment": {
                "bank_name": "Atlantic Commercial Bank",
                "account_name": "Cape Horizon Logistics Pty Ltd",
                "account_number": "XXXX-0048-91",
            },
            "notes": "Late payments may incur a service charge.",
        },
    ]

    invoices.append(build_multi_page_invoice("invoice_007", "classic_blue", "USD"))
    invoices.append(build_multi_page_invoice("invoice_008", "minimal_green", "EUR"))
    return invoices


def build_multi_page_invoice(sample_id: str, template: str, currency: str) -> dict[str, Any]:
    unit_prices = [32.50, 56.00, 78.25, 15.75, 99.99, 42.10, 12.60, 64.80, 88.40, 27.35]
    line_items = []
    for idx in range(1, 23):
        quantity = (idx % 5) + 1
        unit_price = unit_prices[idx % len(unit_prices)]
        line_total = round(quantity * unit_price, 2)
        line_items.append(
            {
                "description": f"Project Item {idx:02d} - Service and materials package",
                "quantity": quantity,
                "unit_price": unit_price,
                "line_total": line_total,
            }
        )

    subtotal = round(sum(item["line_total"] for item in line_items), 2)
    tax = round(subtotal * 0.12, 2)
    shipping = 45.00 if currency != "EUR" else 30.00
    grand_total = round(subtotal + tax + shipping, 2)

    return {
        "sample_id": sample_id,
        "template": template,
        "vendor": {
            "name": "Atlas BuildWorks International",
            "address": "500 Harbor Plaza, Boston, MA 02110, USA" if currency == "USD" else "62 Rue du Port, 13002 Marseille, France",
            "phone": "+1-617-555-0122" if currency == "USD" else "+33-4-55-88-1022",
            "email": "billing@atlas-buildworks.test",
        },
        "customer": {
            "name": "Orchid Property Group" if currency == "USD" else "Helios Facilities BV",
            "address": "18 Cedar Lane, Austin, TX 78701, USA" if currency == "USD" else "Nieuwezijds Voorburgwal 120, 1012 SH Amsterdam, Netherlands",
        },
        "invoice": {
            "invoice_number": f"ATL-{datetime.now().year}-{sample_id[-3:]}",
            "invoice_date": "2026-08-08" if currency == "USD" else "2026-08-03",
            "due_date": "2026-09-07" if currency == "USD" else "2026-09-02",
            "currency": currency,
        },
        "line_items": line_items,
        "totals": {"subtotal": subtotal, "tax": tax, "shipping": shipping, "grand_total": grand_total},
        "payment": {
            "bank_name": "Harbor City Bank" if currency == "USD" else "Union Finance Europe",
            "account_name": "Atlas BuildWorks International",
            "account_number": "XXXX-8844-2101" if currency == "USD" else "EU22 XXXX XXXX 1020",
        },
        "notes": "This sample is intentionally multi-page for OCR and pagination testing.",
    }


def load_fonts() -> dict[str, ImageFont.ImageFont]:
    try:
        title = ImageFont.truetype("DejaVuSans-Bold.ttf", 42)
        heading = ImageFont.truetype("DejaVuSans-Bold.ttf", 24)
        body = ImageFont.truetype("DejaVuSans.ttf", 20)
        small = ImageFont.truetype("DejaVuSans.ttf", 16)
    except OSError:
        title = ImageFont.load_default()
        heading = ImageFont.load_default()
        body = ImageFont.load_default()
        small = ImageFont.load_default()
    return {"title": title, "heading": heading, "body": body, "small": small}


FONTS = load_fonts()


def format_currency(amount: float | int, currency: str) -> str:
    if currency == "JPY":
        return f"JPY {amount:,.0f}"
    if currency == "EUR":
        return f"EUR {amount:,.2f}"
    if currency == "CAD":
        return f"CAD {amount:,.2f}"
    if currency == "ZAR":
        return f"ZAR {amount:,.2f}"
    return f"USD {amount:,.2f}"


def chunked(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [items[idx:idx + size] for idx in range(0, len(items), size)]


def render_invoice_html(invoice: dict[str, Any], pages: int) -> str:
    currency = invoice["invoice"]["currency"]
    rows = "\n".join(
        "<tr>"
        f"<td>{item['description']}</td>"
        f"<td>{item['quantity']}</td>"
        f"<td>{format_currency(item['unit_price'], currency)}</td>"
        f"<td>{format_currency(item['line_total'], currency)}</td>"
        "</tr>"
        for item in invoice["line_items"]
    )
    template = TEMPLATES[invoice["template"]]
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{invoice["sample_id"]}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 40px; color: #222; }}
    h1 {{ color: {template["accent"]}; margin-bottom: 8px; }}
    .meta {{ display: flex; justify-content: space-between; margin-bottom: 24px; }}
    .block {{ width: 48%; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 24px; }}
    th {{ background: {template["table_fill"]}; text-align: left; padding: 10px; }}
    td {{ border-bottom: 1px solid #ddd; padding: 10px; }}
    .totals {{ margin-top: 20px; width: 320px; margin-left: auto; }}
    .totals td {{ border: none; padding: 6px 0; }}
  </style>
</head>
<body>
  <h1>INVOICE</h1>
  <p>Template: {invoice["template"]} | Pages: {pages}</p>
  <div class="meta">
    <div class="block">
      <strong>Vendor</strong><br />
      {invoice["vendor"]["name"]}<br />
      {invoice["vendor"]["address"]}<br />
      {invoice["vendor"]["phone"]}<br />
      {invoice["vendor"]["email"]}
    </div>
    <div class="block">
      <strong>Bill To</strong><br />
      {invoice["customer"]["name"]}<br />
      {invoice["customer"]["address"]}<br /><br />
      <strong>Invoice No:</strong> {invoice["invoice"]["invoice_number"]}<br />
      <strong>Invoice Date:</strong> {invoice["invoice"]["invoice_date"]}<br />
      <strong>Due Date:</strong> {invoice["invoice"]["due_date"]}<br />
      <strong>Currency:</strong> {currency}
    </div>
  </div>
  <table>
    <thead>
      <tr><th>Description</th><th>Qty</th><th>Unit Price</th><th>Line Total</th></tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>
  <table class="totals">
    <tr><td>Subtotal</td><td>{format_currency(invoice["totals"]["subtotal"], currency)}</td></tr>
    <tr><td>Tax</td><td>{format_currency(invoice["totals"]["tax"], currency)}</td></tr>
    <tr><td>Shipping</td><td>{format_currency(invoice["totals"]["shipping"], currency)}</td></tr>
    <tr><td><strong>Grand Total</strong></td><td><strong>{format_currency(invoice["totals"]["grand_total"], currency)}</strong></td></tr>
  </table>
  <p><strong>Notes:</strong> {invoice["notes"]}</p>
</body>
</html>
"""


def draw_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font: ImageFont.ImageFont, fill: str) -> tuple[int, int, int, int]:
    draw.text(xy, text, font=font, fill=fill)
    left, top, right, bottom = draw.textbbox(xy, text, font=font)
    return left, top, right, bottom


def render_page(invoice: dict[str, Any], items: list[dict[str, Any]], page_number: int, page_count: int) -> Image.Image:
    template = TEMPLATES[invoice["template"]]
    currency = invoice["invoice"]["currency"]
    image = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), "white")
    draw = ImageDraw.Draw(image)

    draw.rectangle((0, 0, PAGE_WIDTH, 145), fill=template["accent"])
    draw_text(draw, (MARGIN_X, 42), "INVOICE", FONTS["title"], "white")
    draw_text(draw, (PAGE_WIDTH - 280, 52), f"Page {page_number} / {page_count}", FONTS["body"], "white")

    y = MARGIN_Y + 110
    draw_text(draw, (MARGIN_X, y), invoice["vendor"]["name"], FONTS["heading"], template["accent"])
    y += 34
    for line in [invoice["vendor"]["address"], invoice["vendor"]["phone"], invoice["vendor"]["email"]]:
        draw_text(draw, (MARGIN_X, y), line, FONTS["body"], "#222222")
        y += 28

    right_x = 760
    y = MARGIN_Y + 110
    metadata = [
        ("Invoice No", invoice["invoice"]["invoice_number"]),
        ("Invoice Date", invoice["invoice"]["invoice_date"]),
        ("Due Date", invoice["invoice"]["due_date"]),
        ("Currency", invoice["invoice"]["currency"]),
    ]
    for label, value in metadata:
        draw_text(draw, (right_x, y), f"{label}:", FONTS["heading"], template["accent"])
        draw_text(draw, (right_x + 180, y), value, FONTS["body"], "#222222")
        y += 34

    y += 24
    draw_text(draw, (right_x, y), "Bill To", FONTS["heading"], template["accent"])
    y += 34
    draw_text(draw, (right_x, y), invoice["customer"]["name"], FONTS["body"], "#222222")
    y += 28
    draw_text(draw, (right_x, y), invoice["customer"]["address"], FONTS["body"], "#222222")

    table_y = 470
    draw.rounded_rectangle((MARGIN_X, table_y, PAGE_WIDTH - MARGIN_X, table_y + 46), radius=10, fill=template["table_fill"])
    columns = [
        (MARGIN_X + 24, "Description"),
        (690, "Qty"),
        (810, "Unit Price"),
        (1010, "Line Total"),
    ]
    for x, label in columns:
        draw_text(draw, (x, table_y + 12), label, FONTS["heading"], template["accent"])

    row_y = table_y + 70
    for item in items:
        draw.line((MARGIN_X, row_y + 32, PAGE_WIDTH - MARGIN_X, row_y + 32), fill="#D9D9D9", width=1)
        draw_text(draw, (MARGIN_X + 24, row_y), item["description"][:48], FONTS["body"], "#222222")
        draw_text(draw, (700, row_y), str(item["quantity"]), FONTS["body"], "#222222")
        draw_text(draw, (810, row_y), format_currency(item["unit_price"], currency), FONTS["body"], "#222222")
        draw_text(draw, (1010, row_y), format_currency(item["line_total"], currency), FONTS["body"], "#222222")
        row_y += ROW_HEIGHT

    footer_top = PAGE_HEIGHT - 260
    if page_number == page_count:
        draw.rounded_rectangle((760, footer_top, PAGE_WIDTH - MARGIN_X, PAGE_HEIGHT - 110), radius=12, outline=template["accent"], width=2)
        totals = [
            ("Subtotal", invoice["totals"]["subtotal"]),
            ("Tax", invoice["totals"]["tax"]),
            ("Shipping", invoice["totals"]["shipping"]),
            ("Grand Total", invoice["totals"]["grand_total"]),
        ]
        total_y = footer_top + 24
        for label, amount in totals:
            font = FONTS["heading"] if label == "Grand Total" else FONTS["body"]
            draw_text(draw, (790, total_y), label, font, template["accent"] if label == "Grand Total" else "#222222")
            draw_text(draw, (980, total_y), format_currency(amount, currency), font, "#222222")
            total_y += 38

    draw_text(draw, (MARGIN_X, PAGE_HEIGHT - 210), "Payment Details", FONTS["heading"], template["accent"])
    draw_text(draw, (MARGIN_X, PAGE_HEIGHT - 176), invoice["payment"]["bank_name"], FONTS["body"], "#222222")
    draw_text(draw, (MARGIN_X, PAGE_HEIGHT - 148), invoice["payment"]["account_name"], FONTS["body"], "#222222")
    draw_text(draw, (MARGIN_X, PAGE_HEIGHT - 120), invoice["payment"]["account_number"], FONTS["body"], "#222222")
    draw_text(draw, (MARGIN_X, PAGE_HEIGHT - 82), invoice["notes"], FONTS["small"], template["muted"])
    return image


def build_bbox_summary(items: list[dict[str, Any]], max_rows: int) -> list[dict[str, Any]]:
    summaries = []
    for idx, item in enumerate(items):
        page = idx // max_rows + 1
        row = idx % max_rows
        top = 540 + row * ROW_HEIGHT
        summaries.append(
            {
                "description": item["description"],
                "page": page,
                "bbox": [114, top, 1120, top + 28],
            }
        )
    return summaries


def build_expected_record(invoice: dict[str, Any], page_count: int) -> dict[str, Any]:
    max_rows = TEMPLATES[invoice["template"]]["max_rows"]
    return {
        "sample_id": invoice["sample_id"],
        "template": invoice["template"],
        "page_count": page_count,
        "source_files": {
            "html": f"inputs/{invoice['sample_id']}.html",
            "pdf": f"inputs/{invoice['sample_id']}.pdf",
            "png": [f"inputs/{invoice['sample_id']}_page_{idx}.png" for idx in range(1, page_count + 1)],
        },
        "ground_truth": {
            "vendor_name": invoice["vendor"]["name"],
            "vendor_address": invoice["vendor"]["address"],
            "customer_name": invoice["customer"]["name"],
            "customer_address": invoice["customer"]["address"],
            "invoice_number": invoice["invoice"]["invoice_number"],
            "invoice_date": invoice["invoice"]["invoice_date"],
            "due_date": invoice["invoice"]["due_date"],
            "currency": invoice["invoice"]["currency"],
            "line_items": invoice["line_items"],
            "totals": invoice["totals"],
            "payment": invoice["payment"],
            "notes": invoice["notes"],
        },
        "bounding_boxes": {
            "invoice_number": {"page": 1, "bbox": [940, 190, 1120, 220]},
            "invoice_date": {"page": 1, "bbox": [940, 224, 1120, 254]},
            "due_date": {"page": 1, "bbox": [940, 258, 1120, 288]},
            "vendor_name": {"page": 1, "bbox": [90, 190, 530, 220]},
            "customer_name": {"page": 1, "bbox": [760, 350, 1120, 378]},
            "line_items": build_bbox_summary(invoice["line_items"], max_rows),
            "grand_total": {"page": page_count, "bbox": [980, 1578, 1120, 1608]},
        },
    }


def build_session_record(record: dict[str, Any]) -> dict[str, Any]:
    """Map each generated input to its expected output for demos and evals."""
    return {
        "session_id": record["sample_id"],
        "input": record["source_files"],
        "expected_output": f"expected/{record['sample_id']}.json",
        "summary": (
            f"{record['template']} invoice in {record['ground_truth']['currency']} "
            f"with {len(record['ground_truth']['line_items'])} line items "
            f"across {record['page_count']} page(s)."
        ),
    }


def ensure_clean_dirs() -> None:
    for path in [INPUTS_DIR, EXPECTED_DIR]:
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)


def save_outputs(invoice: dict[str, Any]) -> dict[str, Any]:
    max_rows = TEMPLATES[invoice["template"]]["max_rows"]
    page_groups = chunked(invoice["line_items"], max_rows)
    page_count = len(page_groups)

    html = render_invoice_html(invoice, page_count)
    (INPUTS_DIR / f"{invoice['sample_id']}.html").write_text(html, encoding="utf-8")

    images = []
    for page_number, items in enumerate(page_groups, start=1):
        image = render_page(invoice, items, page_number, page_count)
        png_path = INPUTS_DIR / f"{invoice['sample_id']}_page_{page_number}.png"
        image.save(png_path, "PNG")
        images.append(image.convert("RGB"))

    pdf_path = INPUTS_DIR / f"{invoice['sample_id']}.pdf"
    first, *rest = images
    first.save(pdf_path, "PDF", resolution=150.0, save_all=True, append_images=rest)

    expected = build_expected_record(invoice, page_count)
    expected_path = EXPECTED_DIR / f"{invoice['sample_id']}.json"
    expected_path.write_text(json.dumps(expected, indent=2), encoding="utf-8")
    return expected


def main() -> None:
    ensure_clean_dirs()
    aggregate = [save_outputs(invoice) for invoice in sample_invoices()]
    AGGREGATE_JSON.write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
    sessions = [build_session_record(record) for record in aggregate]
    SESSIONS_JSON.write_text(json.dumps(sessions, indent=2), encoding="utf-8")
    print(f"Generated {len(aggregate)} invoices into {INPUTS_DIR}")
    print(f"Wrote aggregate golden set to {AGGREGATE_JSON}")
    print(f"Wrote session manifest to {SESSIONS_JSON}")


if __name__ == "__main__":
    main()
