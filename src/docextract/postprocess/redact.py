"""PII redaction helpers for privacy compliance (w24/w30)."""

from __future__ import annotations

import copy
import re
from typing import Any


def mask_string(val: str, keep_start: int = 1, keep_end: int = 1) -> str:
    """Mask sensitive string while keeping edge hints."""
    if not val or len(val) <= keep_start + keep_end:
        return "[REDACTED]"
    return val[:keep_start] + "*" * (len(val) - keep_start - keep_end) + val[-keep_end:]


def redact_invoice_data(invoice_data: dict[str, Any]) -> dict[str, Any]:
    """Return a deep copy of invoice data with customer PII redacted."""
    redacted = copy.deepcopy(invoice_data)

    # Redact customer identity
    if "customer_name" in redacted and redacted["customer_name"]:
        redacted["customer_name"] = mask_string(redacted["customer_name"], 2, 2)

    # Redact customer address
    if "customer_address" in redacted and redacted["customer_address"]:
        redacted["customer_address"] = "[REDACTED ADDRESS]"

    # Mask account numbers if present
    payment = redacted.get("payment")
    if isinstance(payment, dict) and "account_number" in payment:
        acc = payment["account_number"]
        if acc:
            digits = re.sub(r"\D", "", acc)
            last4 = digits[-4:] if len(digits) >= 4 else "XXXX"
            payment["account_number"] = f"XXXX-XXXX-{last4}"

    return redacted
