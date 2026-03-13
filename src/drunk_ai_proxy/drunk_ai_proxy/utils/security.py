"""Comprehensive security utilities for FastAPI and FastMCP resources.

This module provides reusable security functions following the security standards
defined in docs/security/SECURITY_STANDARDS.md.

Functions are organized into categories:
- Error handling & sanitization
- URL & path validation
- Input validation helpers
- Secrets masking for safe logging
- Audit logging
"""

from __future__ import annotations

import re
from ipaddress import ip_address
from logging import Logger
from pathlib import Path
from urllib.parse import urlparse

from fastapi import UploadFile
from fastapi.responses import JSONResponse
from pydantic import ValidationError


# ============================================================================
# ERROR HANDLING & SANITIZATION
# ============================================================================

def sanitize_error_response(
    user_message: str = "An error occurred while processing your request",
    status_code: int = 400,
    log_context: str = "",
) -> JSONResponse:
    """Create a sanitized error response for clients.

    Args:
        user_message: User-facing error message (should be generic or actionable).
        status_code: HTTP status code (default 400).
        log_context: Context string for logging (not exposed to client).

    Returns:
        JSONResponse with sanitized error and status code.

    Example:
        >>> response = sanitize_error_response(
        ...     user_message="Invalid input provided",
        ...     status_code=400,
        ...     log_context="chat_completions validation"
        ... )
        >>> response.status_code
        400
    """
    return JSONResponse(
        content={"error": user_message},
        status_code=status_code
    )


_USER_ACTIONABLE_KEYWORDS = {
    "required", "missing", "invalid", "format", "range", "length",
    "unauthorized", "forbidden", "timeout", "limit", "rate",
    "unsupported", "deprecated", "malformed", "invalid",
}


def is_user_actionable_error(error_message: str) -> bool:
    """Check if an exception message is safe to expose to users.

    Safe messages contain keywords that help users fix the issue without
    exposing internal implementation details.

    Args:
        error_message: Exception message string to check.

    Returns:
        True if the message contains user-actionable keywords.

    Example:
        >>> is_user_actionable_error("Invalid model format. Expected 'provider_model'")
        True
        >>> is_user_actionable_error("Database connection pooling exhausted")
        False
    """
    lower_msg = error_message.lower()
    return any(keyword in lower_msg for keyword in _USER_ACTIONABLE_KEYWORDS)


def get_actionable_message(error: Exception) -> str:
    """Extract actionable message from exception or return default.

    Args:
        error: Exception instance.

    Returns:
        Actionable error message if detectable, generic message otherwise.
    """
    error_str = str(error).lower()
    if is_user_actionable_error(error_str):
        # Safe to expose original message
        return str(error)
    # Generic message for internal errors
    return "An error occurred while processing your request"


def handle_validation_error(error: ValidationError) -> JSONResponse:
    """Convert Pydantic ValidationError to sanitized JSONResponse.

    Args:
        error: Pydantic ValidationError instance.

    Returns:
        JSONResponse with field validation errors.

    Example:
        >>> from pydantic import BaseModel, validator
        >>> class MyModel(BaseModel):
        ...     value: int
        ...     @validator('value')
        ...     def validate_range(cls, v):
        ...         if v < 0:
        ...             raise ValueError("Must be positive")
        ...         return v
        >>> try:
        ...     MyModel(value=-1)
        ... except ValidationError as e:
        ...     response = handle_validation_error(e)
        ...     response.status_code
        422
    """
    errors: list[dict[str, str]] = []
    for err in error.errors():
        field = ".".join(str(x) for x in err["loc"])
        msg = err["msg"]
        errors.append({"field": field, "error": msg})

    return JSONResponse(
        content={"validation_errors": errors},
        status_code=422
    )


# ============================================================================
# URL & SSRF PREVENTION
# ============================================================================

def validate_url(
    url: str,
    allowed_schemes: list[str] | None = None,
    blocked_hosts: list[str] | None = None,
    require_public_ip: bool = False,
) -> JSONResponse | None:
    """Validate URL to prevent SSRF attacks.

    Args:
        url: URL to validate.
        allowed_schemes: Whitelist of allowed schemes (default ['https']).
        blocked_hosts: Blacklist of blocked hostnames/IPs (default includes localhost).
        require_public_ip: If True, reject private IP ranges (127.0.0.0/8, 10.0.0.0/8, etc).

    Returns:
        JSONResponse with validation error if invalid, None if valid.

    Example:
        >>> error = validate_url("http://localhost/admin")
        >>> error.status_code
        400
        >>> validate_url("https://example.com") is None
        True
    """
    if not url:
        return sanitize_error_response("URL is required", 400)

    allowed_schemes = allowed_schemes or ["https"]
    blocked_hosts = blocked_hosts or ["localhost", "127.0.0.1", "::1", "0.0.0.0"]

    try:
        parsed = urlparse(url)
    except Exception:
        return sanitize_error_response("Invalid URL format", 400)

    # Check scheme
    if parsed.scheme not in allowed_schemes:
        return sanitize_error_response(
            f"Only {', '.join(allowed_schemes)} URLs allowed",
            400
        )

    # Check hostname
    hostname = parsed.hostname or parsed.netloc
    if not hostname:
        return sanitize_error_response("URL must have hostname", 400)

    # Check blacklist
    if hostname in blocked_hosts:
        return sanitize_error_response("Access to this hostname is not allowed", 400)

    # Check private IPs
    if require_public_ip:
        try:
            ip = ip_address(hostname)
            # Check if private
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                return sanitize_error_response(
                    "Private IP addresses not allowed",
                    400
                )
        except ValueError:
            # Not an IP address, that's fine
            pass

    return None


# ============================================================================
# PATH TRAVERSAL PREVENTION
# ============================================================================

def safe_path_join(base_dir: Path | str, user_path: str) -> Path | None:
    """Safely join user-provided path with base directory.

    Prevents directory traversal attacks by verifying the final path
    is within the base directory.

    Args:
        base_dir: Base directory (safe, operator-controlled).
        user_path: User-provided path component.

    Returns:
        Safely joined Path if valid, None if traversal detected.

    Example:
        >>> safe_path_join(Path("/app/data"), "config.yaml")
        Path('/app/data/config.yaml')
        >>> safe_path_join(Path("/app/data"), "../../../etc/passwd") is None
        True
    """
    if not user_path:
        return None

    base = Path(base_dir).resolve()

    # Reject paths with suspicious patterns
    if ".." in user_path or user_path.startswith("/"):
        return None

    # Allow only safe characters
    if not re.match(r"^[\w\-./]+$", user_path):
        return None

    try:
        # Join and resolve symlinks
        full_path = (base / user_path).resolve()

        # Verify result is within base directory
        if not str(full_path).startswith(str(base)):
            return None

        return full_path
    except (ValueError, RuntimeError):
        return None


# ============================================================================
# FILE UPLOAD VALIDATION
# ============================================================================

async def validate_file_upload(
    file: UploadFile,
    allowed_extensions: list[str] | None = None,
    allowed_mimetypes: list[str] | None = None,
    max_size_mb: int = 10,
) -> JSONResponse | None:
    """Validate file upload before processing.

    Args:
        file: UploadFile instance from request.
        allowed_extensions: Whitelist of file extensions (e.g., ['.md', '.txt']).
        allowed_mimetypes: Whitelist of MIME types.
        max_size_mb: Maximum file size in megabytes.

    Returns:
        JSONResponse with validation error if invalid, None if valid.

    Example:
        >>> # In async endpoint:
        >>> error = await validate_file_upload(
        ...     file,
        ...     allowed_extensions=['.md', '.txt'],
        ...     max_size_mb=5
        ... )
        >>> if error:
        ...     return error
    """
    if not file or not file.filename:
        return sanitize_error_response("File is required", 400)

    # Check filename
    filename = file.filename
    if ".." in filename or "/" in filename or "\\" in filename:
        return sanitize_error_response("Invalid filename", 400)

    # Check extension
    if allowed_extensions:
        file_ext = Path(filename).suffix.lower()
        if file_ext not in allowed_extensions:
            return sanitize_error_response(
                f"File type not allowed. Allowed: {', '.join(allowed_extensions)}",
                400
            )

    # Check MIME type
    if allowed_mimetypes and file.content_type not in allowed_mimetypes:
        return sanitize_error_response(
            f"MIME type '{file.content_type}' not allowed",
            400
        )

    # Check size
    # Note: This reads the file into memory, which is fine for size check
    try:
        content = await file.read()
        size_mb = len(content) / (1024 * 1024)
        if size_mb > max_size_mb:
            return sanitize_error_response(
                f"File size exceeds {max_size_mb} MB limit",
                413  # Payload Too Large
            )
        # Reset file position for later reading
        await file.seek(0)
    except Exception:
        return sanitize_error_response("Error reading file", 400)

    return None


# ============================================================================
# SECRETS MASKING FOR LOGGING
# ============================================================================

def mask_sensitive_value(
    value: object,
    key: str = "",
    show_chars: int = 4,
) -> str:
    """Mask sensitive value for safe logging.

    Detects sensitive keys and shows only last N characters.

    Args:
        value: Value to potentially mask.
        key: Key/field name (used to detect if value is sensitive).
        show_chars: Number of characters to show at end.

    Returns:
        Masked value string or full value if not sensitive.

    Example:
        >>> mask_sensitive_value("sk_live_abc123xyz", key="api_key")
        '...xyz'
        >>> mask_sensitive_value("public_value", key="status")
        'public_value'
    """
    if value is None:
        return "[None]"

    if not isinstance(value, str):
        return str(value)

    # Check if key looks like it contains sensitive data
    sensitive_keywords = {
        "token", "key", "secret", "password", "credential",
        "auth", "bearer", "api_key", "private_key", "session_id",
    }

    key_lower = key.lower() if key else ""
    is_sensitive = any(kw in key_lower for kw in sensitive_keywords)

    if not is_sensitive:
        return value

    # Mask sensitive values
    if len(value) <= show_chars:
        return "..." + "*" * len(value)

    return "..." + value[-show_chars:]


# ============================================================================
# AUDIT LOGGING
# ============================================================================

def audit_log(
    logger: Logger,
    event: str,
    status: str = "unknown",
    user_id: str | None = None,
    resource: str | None = None,
    details: dict[str, object] | None = None,
    **kwargs: object,
) -> None:
    """Log security-relevant events for audit trail.

    Structured logging for security events like auth, access control, errors.

    Args:
        logger: Logger instance.
        event: Event type (e.g., 'authorization_failed', 'resource_accessed').
        status: Event status (e.g., 'success', 'denied', 'failed').
        user_id: User or client identifier (if applicable).
        resource: Resource accessed (e.g., '/admin/users').
        details: Additional structured details.
        **kwargs: Additional key=value pairs to log.

    Example:
        >>> from logging import getLogger
        >>> logger = getLogger(__name__)
        >>> audit_log(
        ...     logger,
        ...     event="resource_accessed",
        ...     status="success",
        ...     user_id="user_123",
        ...     resource="/api/data",
        ... )
    """
    audit_data: dict[str, object] = {
        "event": event,
        "status": status,
    }

    if user_id:
        audit_data["user_id"] = user_id
    if resource:
        audit_data["resource"] = resource
    if details:
        audit_data["details"] = details

    audit_data.update(kwargs)

    # Use info level for audit events (always visible)
    logger.info("AUDIT: %s", audit_data)


# ============================================================================
# REQUEST/RESPONSE UTILITIES
# ============================================================================

def validate_request_size(
    content_length: int | str | None,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
) -> JSONResponse | None:
    """Validate request Content-Length before processing.

    Args:
        content_length: Content-Length header value.
        max_bytes: Maximum allowed size in bytes.

    Returns:
        JSONResponse with error if too large, None if acceptable.
    """
    if content_length is None:
        return None

    try:
        size = int(content_length) if isinstance(content_length, str) else content_length
        if size > max_bytes:
            max_mb = max_bytes / (1024 * 1024)
            return sanitize_error_response(
                f"Request size exceeds {max_mb} MB limit",
                413
            )
    except (ValueError, TypeError):
        return sanitize_error_response("Invalid Content-Length", 400)

    return None


def validate_content_type(
    content_type: str | None,
    expected_types: list[str],
) -> JSONResponse | None:
    """Validate Content-Type header.

    Args:
        content_type: Content-Type header value.
        expected_types: List of acceptable MIME types (e.g., ['application/json']).

    Returns:
        JSONResponse with error if not matching, None if valid.

    Example:
        >>> error = validate_content_type(
        ...     "text/plain",
        ...     expected_types=["application/json"]
        ... )
        >>> error.status_code
        415
    """
    if not content_type:
        return sanitize_error_response("Content-Type header required", 400)

    # Extract base type (handle charset etc)
    base_type = content_type.split(";")[0].strip().lower()

    if not any(exp.lower() in base_type for exp in expected_types):
        return sanitize_error_response(
            f"Content-Type must be one of: {', '.join(expected_types)}",
            415  # Unsupported Media Type
        )

    return None


class SecurityUtils:
    """Static utility wrapper for security helper functions."""

    USER_ACTIONABLE_KEYWORDS = _USER_ACTIONABLE_KEYWORDS

    sanitize_error_response = staticmethod(sanitize_error_response)
    is_user_actionable_error = staticmethod(is_user_actionable_error)
    get_actionable_message = staticmethod(get_actionable_message)
    handle_validation_error = staticmethod(handle_validation_error)
    validate_url = staticmethod(validate_url)
    safe_path_join = staticmethod(safe_path_join)
    validate_file_upload = staticmethod(validate_file_upload)
    mask_sensitive_value = staticmethod(mask_sensitive_value)
    audit_log = staticmethod(audit_log)
    validate_request_size = staticmethod(validate_request_size)
    validate_content_type = staticmethod(validate_content_type)


sanitize_error_response = SecurityUtils.sanitize_error_response
is_user_actionable_error = SecurityUtils.is_user_actionable_error
get_actionable_message = SecurityUtils.get_actionable_message
handle_validation_error = SecurityUtils.handle_validation_error
validate_url = SecurityUtils.validate_url
safe_path_join = SecurityUtils.safe_path_join
validate_file_upload = SecurityUtils.validate_file_upload
mask_sensitive_value = SecurityUtils.mask_sensitive_value
audit_log = SecurityUtils.audit_log
validate_request_size = SecurityUtils.validate_request_size
validate_content_type = SecurityUtils.validate_content_type
