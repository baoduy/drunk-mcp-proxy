"""Error handling helpers."""

from __future__ import annotations


def sanitize_error_message(_: str) -> str:
    """Return a safe error message for client responses.

    Args:
        _: Raw error message (ignored).

    Returns:
        Sanitized error message.
    """
    return "An error occurred while processing the request"
