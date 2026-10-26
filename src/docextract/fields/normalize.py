"""Normalize extracted strings into canonical values.

Each function takes a possibly-messy string and returns a clean canonical value or None if it cannot be parsed. Canonical types:
    - date -> "YYYY-MM-DD" string
    - amount -> float (no currency symbol, no thousands separator)
"""

from __future__ import annotations  # type hints

import re
from datetime import datetime

_DATE_FORMATS: tuple[tuple[str, str], ...] = (
    ("%Y-%m-%d", "%Y-%m-%d"),   # ISO: 2026-08-10
    ("%d/%m/%Y", "%Y-%m-%d"),   # 25/12/2026
    ("%m/%d/%Y", "%Y-%m-%d"),   # 12/25/2026
    ("%d-%m-%Y", "%Y-%m-%d"),   # 25-12-2026
    ("%Y/%m/%d", "%Y-%m-%d"),   # 2026/08/10
    ("%d.%m.%Y", "%Y-%m-%d"),   # 25.12.2026
    ("%Y.%m.%d", "%Y-%m-%d"),   # 2026.12.25
    ("%d/%m/%y", "%Y-%m-%d"),   # 25/12/26
    ("%m/%d/%y", "%Y-%m-%d"),   # 12/25/26
    ("%d-%m-%y", "%Y-%m-%d"),   # 25-12-26
    ("%d.%m.%y", "%Y-%m-%d"),   # 25.12.26
    ("%b %d %Y", "%Y-%m-%d"),   # Mar 06 2012 / Mar 6 2012
    ("%b %d, %Y", "%Y-%m-%d"),  # Aug 10, 2026
    ("%B %d %Y", "%Y-%m-%d"),   # March 06 2012
    ("%B %d, %Y", "%Y-%m-%d"),  # August 10, 2026
    ("%d %b %Y", "%Y-%m-%d"),   # 10 Aug 2026
    ("%d %B %Y", "%Y-%m-%d"),   # 10 August 2026
    ("%d-%b-%Y", "%Y-%m-%d"),   # 10-Aug-2026
    ("%d-%B-%Y", "%Y-%m-%d"),   # 10-August-2026
    ("%b-%d-%Y", "%Y-%m-%d"),   # Mar-06-2012
    ("%b.%d.%Y", "%Y-%m-%d"),   # Mar.06.2012
)

# amount normalizer 
# regex pieces used to clean amount strings. `_CURRENCY_CHARS` matches a leading currency symbol 
_CURRENCY_CHARS = re.compile(r"^\s*[$€£]|^\s*(?:USD|EUR|GBP|JPY|CAD)\s*", re.IGNORECASE)


def normalize_date(value: str) -> str | None:
    """Return the canonical 'YYYY-MM-DD' from a date string or none.
    tries several common formats. if none match returns None.
    """

    cleaned = value.strip().rstrip(".,;")
    cleaned = re.sub(r"\s+", " ", cleaned)
    for input_fmt, output_fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(cleaned, input_fmt) 
            return parsed.strftime(output_fmt)  
        except ValueError:
            continue
    return None


def normalize_amount(value: str) -> float | None:
    """Return the canonical float value of a money string or none.
    Accepts: '$1,234.56', '1.234,56', '1234.56', '1,234', 'USD 99.00'
    Strips currency symobols and thousands separator
    """
    cleaned = value.strip()
    # remove leading currency symbol if present
    cleaned = _CURRENCY_CHARS.sub("", cleaned).strip()

    if "," in cleaned and "." in cleaned:
        # both present: rightmost is the decimal separator
        if cleaned.rfind(",") > cleaned.rfind("."):
            # comma is the decimal "1.234,56" -> "1234.56"
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            # dot is the decimal "1,234.56" -> "1234.56"
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        # only commas. if exactly one comma followed by 1-2 digits, treat as decimal
        if re.match(r"^\d+,\d{1,2}$", cleaned):
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")

    try:
        return float(cleaned)
    except ValueError:
        return None