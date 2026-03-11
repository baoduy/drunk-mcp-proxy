"""Tests for security utilities module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock
from pydantic import BaseModel, ValidationError

from drunk_ai_proxy.utils.security import (
    sanitize_error_response,
    is_user_actionable_error,
    get_actionable_message,
    handle_validation_error,
    validate_url,
    safe_path_join,
    mask_sensitive_value,
    audit_log,
    validate_request_size,
    validate_content_type,
)


class TestSanitizeErrorResponse:
    """Test error sanitization."""

    def test_default_error_response(self) -> None:
        """Default error response is generic."""
        response = sanitize_error_response()
        assert response.status_code == 400

    def test_custom_error_message(self) -> None:
        """Custom error messages are preserved."""
        response = sanitize_error_response(
            user_message="Invalid input",
            status_code=400,
        )
        assert response.status_code == 400
        assert b"Invalid input" in response.body

    def test_custom_status_code(self) -> None:
        """Custom status codes are used."""
        response = sanitize_error_response(
            user_message="Not found",
            status_code=404,
        )
        assert response.status_code == 404


class TestUserActionableError:
    """Test detection of actionable error messages."""

    def test_required_field_error(self) -> None:
        """Required field messages are actionable."""
        assert is_user_actionable_error("Field 'email' is required")
        assert is_user_actionable_error("Missing required field")

    def test_invalid_format_error(self) -> None:
        """Format validation errors are actionable."""
        assert is_user_actionable_error("Invalid email format")
        assert is_user_actionable_error("Expected format: 'provider_model'")

    def test_rate_limit_error(self) -> None:
        """Rate limit errors are actionable."""
        assert is_user_actionable_error("Rate limit exceeded")
        assert is_user_actionable_error("Request limit exceeded")

    def test_internal_error(self) -> None:
        """Internal errors are not actionable."""
        assert not is_user_actionable_error("Database connection pooling exhausted")
        assert not is_user_actionable_error("Memory allocation failed")


class TestGetActionableMessage:
    """Test extraction of actionable messages."""

    def test_actionable_exception(self) -> None:
        """Actionable exceptions return their message."""
        error = ValueError("Invalid format expected")
        msg = get_actionable_message(error)
        assert "Invalid format" in msg

    def test_non_actionable_exception(self) -> None:
        """Non-actionable exceptions return generic message."""
        error = RuntimeError("Database connection pooling exhausted")
        msg = get_actionable_message(error)
        assert msg == "An error occurred while processing your request"


class TestHandleValidationError:
    """Test Pydantic validation error handling."""

    def test_validation_error_conversion(self) -> None:
        """ValidationError converted to JSONResponse."""
        class Model(BaseModel):
            value: int

        try:
            # Trigger validation error by passing invalid type
            Model(value="not an int")  # type: ignore
        except ValidationError as e:
            response = handle_validation_error(e)
            assert response.status_code == 422


class TestValidateUrl:
    """Test URL validation for SSRF prevention."""

    def test_https_url_accepted(self) -> None:
        """HTTPS URLs are accepted by default."""
        error = validate_url("https://example.com/file.md")
        assert error is None

    def test_http_url_rejected(self) -> None:
        """HTTP URLs are rejected by default."""
        error = validate_url("http://example.com/file.md")
        assert error is not None
        assert error.status_code == 400

    def test_localhost_blocked(self) -> None:
        """Localhost is blocked by default."""
        error = validate_url("https://localhost/admin")
        assert error is not None
        assert error.status_code == 400

    def test_loopback_ip_blocked(self) -> None:
        """Loopback IPs are blocked by default."""
        error = validate_url("https://127.0.0.1/admin")
        assert error is not None
        assert error.status_code == 400

    def test_custom_scheme_whitelist(self) -> None:
        """Custom scheme allowlist works."""
        error = validate_url(
            "ftp://example.com/file",
            allowed_schemes=["ftp", "https"],
        )
        assert error is None

    def test_private_ip_rejected(self) -> None:
        """Private IPs rejected when require_public_ip=True."""
        error = validate_url(
            "https://10.0.0.1/data",
            require_public_ip=True,
        )
        assert error is not None
        assert error.status_code == 400

    def test_custom_blocked_hosts(self) -> None:
        """Custom blocked host list works."""
        error = validate_url(
            "https://internal-api.local/data",
            blocked_hosts=["internal-api.local"],
        )
        assert error is not None


class TestSafePathJoin:
    """Test path traversal prevention."""

    def test_safe_relative_path(self) -> None:
        """Safe relative paths are accepted."""
        base = Path("/app/data")
        result = safe_path_join(base, "config.yaml")
        assert result is not None
        assert "config.yaml" in str(result)

    def test_parent_traversal_rejected(self) -> None:
        """Parent directory traversal rejected."""
        base = Path("/app/data")
        result = safe_path_join(base, "../../../etc/passwd")
        assert result is None

    def test_absolute_path_rejected(self) -> None:
        """Absolute paths rejected."""
        base = Path("/app/data")
        result = safe_path_join(base, "/etc/passwd")
        assert result is None

    def test_nested_relative_path(self) -> None:
        """Nested relative paths work."""
        base = Path("/app/data")
        result = safe_path_join(base, "config/server.yaml")
        assert result is not None

    def test_suspicious_patterns_rejected(self) -> None:
        """Suspicious patterns rejected."""
        base = Path("/app/data")
        assert safe_path_join(base, ".bashrc") is not None  # Leading dot is ok
        assert safe_path_join(base, "file<script>") is None  # Invalid chars


class TestMaskSensitiveValue:
    """Test sensitive value masking for logging."""

    def test_api_key_masked(self) -> None:
        """API keys are masked."""
        masked = mask_sensitive_value("sk_live_abc123xyz", key="api_key")
        assert masked == "...3xyz"
        assert "abc123" not in masked

    def test_token_masked(self) -> None:
        """Tokens are masked."""
        masked = mask_sensitive_value("eyJhbGc...", key="token")
        assert masked.endswith("...")
        assert "eyJhbGc" not in masked

    def test_non_sensitive_not_masked(self) -> None:
        """Non-sensitive values not masked."""
        value = "public_value"
        masked = mask_sensitive_value(value, key="status")
        assert masked == value

    def test_short_sensitive_value(self) -> None:
        """Short sensitive values show asterisks."""
        masked = mask_sensitive_value("abc", key="password")
        assert "*" in masked
        assert "abc" not in masked

    def test_none_value_handled(self) -> None:
        """None values handled gracefully."""
        masked = mask_sensitive_value(None, key="key")
        assert masked == "[None]"


class TestValidateRequestSize:
    """Test request size validation."""

    def test_small_request_accepted(self) -> None:
        """Requests below limit are accepted."""
        error = validate_request_size("1000", max_bytes=10_000)
        assert error is None

    def test_large_request_rejected(self) -> None:
        """Requests exceeding limit are rejected."""
        error = validate_request_size("20_000_000", max_bytes=10_000_000)
        assert error is not None
        assert error.status_code == 413

    def test_no_content_length(self) -> None:
        """Missing Content-Length is allowed."""
        error = validate_request_size(None)
        assert error is None

    def test_invalid_content_length(self) -> None:
        """Invalid Content-Length is rejected."""
        error = validate_request_size("not_a_number")
        assert error is not None
        assert error.status_code == 400


class TestValidateContentType:
    """Test Content-Type validation."""

    def test_exact_match(self) -> None:
        """Exact MIME type matches."""
        error = validate_content_type(
            "application/json",
            expected_types=["application/json"],
        )
        assert error is None

    def test_with_charset(self) -> None:
        """Content-Type with charset accepted."""
        error = validate_content_type(
            "application/json; charset=utf-8",
            expected_types=["application/json"],
        )
        assert error is None

    def test_wrong_type_rejected(self) -> None:
        """Wrong MIME type rejected."""
        error = validate_content_type(
            "text/plain",
            expected_types=["application/json"],
        )
        assert error is not None
        assert error.status_code == 415

    def test_missing_content_type(self) -> None:
        """Missing Content-Type rejected."""
        error = validate_content_type(None, expected_types=["application/json"])
        assert error is not None
        assert error.status_code == 400


class TestAuditLog:
    """Test audit logging."""

    def test_basic_audit_event(self) -> None:
        """Basic audit event logged."""
        logger = Mock()
        audit_log(
            logger,
            event="user_login",
            status="success",
            user_id="user_123",
        )
        logger.info.assert_called_once()
        call_args = logger.info.call_args
        assert "AUDIT" in call_args[0][0]

    def test_audit_with_details(self) -> None:
        """Audit event with details logged."""
        logger = Mock()
        audit_log(
            logger,
            event="config_change",
            status="success",
            user_id="admin_1",
            resource="/config",
            details={"field": "timeout", "old_value": "30", "new_value": "60"},
        )
        logger.info.assert_called_once()

    def test_audit_with_kwargs(self) -> None:
        """Audit event with extra kwargs logged."""
        logger = Mock()
        audit_log(
            logger,
            event="api_call",
            status="success",
            endpoint="/api/data",
            method="GET",
            response_time_ms=150,
        )
        logger.info.assert_called_once()
