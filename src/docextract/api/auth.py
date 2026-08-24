"""API key authentication for the extract endpoint.
Open by default no key set for local/dev.
"""

import os

from fastapi import Header, HTTPException, status

# read once at import, no key = auth disabled
_API_KEY = os.environ.get("DOCEXTRACT_API_KEY", "")


def require_api_key(
        x_api_key: str | None = Header(default=None, alias="X-API-Key")
) -> None:
    """Reject the request unless a valid API key is supplied.
    Returns nothing on success, raise 401 otherwise."""

    # no key configured - open access for dev
    if not _API_KEY:
        return
    # key configured but request has none or the wrong one deny
    if not x_api_key or x_api_key != _API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )