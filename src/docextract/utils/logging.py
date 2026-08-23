import logging
import uuid


def get_logger(name: str) -> logging.Logger:
    """Return a logger pre-configured for this app."""
    return logging.getLogger(name)


def new_request_id() -> str:
    """Create a fresh unique ID for one HTTP request."""
    return f"req_{uuid.uuid4().hex[:12]}"