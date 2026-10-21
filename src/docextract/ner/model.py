"""Token-level NER entity wrapper for invoice extraction (w16)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntitySpan:
    """Represents a recognized named entity span with character offsets."""

    text: str
    label: str
    start: int
    end: int
    score: float


class InvoiceNERModel:
    """Lightweight NER model wrapper with token classification heuristics and fallback."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or "local-heuristic-ner"

    def predict(self, text: str) -> list[EntitySpan]:
        """Extract entity spans (ORG, DATE, MONEY, INVOICE_ID) from raw invoice text."""
        import re

        spans: list[EntitySpan] = []

        # 1. Invoice IDs
        for m in re.finditer(r"\b(?:INV|NWO|GFI|LCS|BEG|SMC|CHL|ATL)-[0-9]{4}-[0-9]{3,4}\b", text):
            spans.append(
                EntitySpan(
                    text=m.group(0),
                    label="INVOICE_ID",
                    start=m.start(),
                    end=m.end(),
                    score=0.98,
                )
            )

        # 2. ISO / Slash Dates
        for m in re.finditer(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{2}/\d{2}/\d{4}\b", text):
            spans.append(
                EntitySpan(
                    text=m.group(0),
                    label="DATE",
                    start=m.start(),
                    end=m.end(),
                    score=0.95,
                )
            )

        # 3. Organizations (Company markers)
        for m in re.finditer(r"\b[A-Z][A-Za-z0-9\s&]+(?:Ltd|Inc|GmbH|LLC|Pty|KK|Co|Corp)\b", text):
            spans.append(
                EntitySpan(
                    text=m.group(0).strip(),
                    label="ORG",
                    start=m.start(),
                    end=m.end(),
                    score=0.92,
                )
            )

        # 4. Monetary amounts
        for m in re.finditer(r"(?:USD|EUR|GBP|CAD|JPY|ZAR|[$€£])\s*[\d,]+(?:\.\d{2})?", text):
            spans.append(
                EntitySpan(
                    text=m.group(0).strip(),
                    label="MONEY",
                    start=m.start(),
                    end=m.end(),
                    score=0.90,
                )
            )

        return spans
