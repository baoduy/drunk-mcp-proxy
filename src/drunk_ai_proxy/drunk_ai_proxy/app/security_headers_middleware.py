"""Compatibility re-export for security middleware classes."""

from __future__ import annotations

from drunk_ai_proxy.middleware.security_headers import (
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)

__all__ = ["SecurityHeadersMiddleware", "RequestSizeLimitMiddleware"]
