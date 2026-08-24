"""Structured invoice extraction schema(the interpreted layer).

Mirrors the golden-set shape so the same model validates both hand-written golden files and extractor output.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LineItem(BaseModel):
    """One row of an invoice's itemized line table."""

    model_config = ConfigDict(extra="forbid")

    # Reject negative or zero quantities/prices, require non-empty text
    description: str = Field(..., min_length=1, description="Item name or description")
    quantity: float = Field(..., gt=0, description="Quantity purchased")
    unit_price: float = Field(..., gt=0, description="Price per unit")
    line_total: float = Field(..., gt=0, description="quantity * unit_price")


class Totals(BaseModel):
    """The invoice's monetary summary."""

    model_config = ConfigDict(extra="forbid")

    subtotal: float = Field(..., ge=0, description="Sum of line items")
    tax: float = Field(..., ge=0, description="Tax amount")
    shipping: float = Field(..., ge=0, description="Shipping amount")
    grand_total: float = Field(..., ge=0, description="Final amount owed")


class ExtractionResult(BaseModel):
    """The fully extracted invoice, matching the golden ground_truth"""

    model_config = ConfigDict(extra="forbid")

    vendor_name: str = Field(..., min_length=1)
    vendor_address: str = Field(...)
    customer_name: str = Field(...)
    customer_address: str = Field(...)
    invoice_number: str = Field(..., min_length=1)
    invoice_date: str = Field(...) 
    due_date: str = Field(...)
    currency: str = Field(..., min_length=3, max_length=3) 
    line_items: list[LineItem] = Field(..., min_length=1)
    totals: Totals