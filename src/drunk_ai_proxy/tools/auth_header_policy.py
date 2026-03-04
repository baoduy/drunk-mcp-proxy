"""Shared authorization header policy helpers."""

from __future__ import annotations

from collections.abc import Sequence

DEFAULT_ANONYMOUS_PATHS: tuple[str, ...] = (
    "/",
    "/health",
    "/docs",
    "/openapi.json",
)


def is_anonymous_path(
    request_path: str | None,
    anonymous_paths: Sequence[str] | None = None,
) -> bool:
    """Return True when the request path should skip auth checks.

    Args:
        request_path: Request path string.
        anonymous_paths: Optional override list of anonymous paths.

    Returns:
        True when auth should be skipped.
    """
    if not request_path:
        return False

    allowed = anonymous_paths or DEFAULT_ANONYMOUS_PATHS
    return request_path in allowed
