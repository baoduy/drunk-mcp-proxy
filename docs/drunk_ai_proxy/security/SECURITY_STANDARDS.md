# Security Standards for FastAPI & FastMCP Resources

**Version:** 1.0  
**Last Updated:** March 2026  
**Scope:** All FastAPI providers, FastMCP resources, middleware, and utility modules

---

## Table of Contents

1. [Core Security Principles](#core-security-principles)
2. [Error Handling & Information Disclosure](#error-handling--information-disclosure)
3. [Authentication & Authorization](#authentication--authorization)
4. [Input Validation](#input-validation)
5. [Rate Limiting & DoS Prevention](#rate-limiting--dos-prevention)
6. [CORS & Cross-Origin Security](#cors--cross-origin-security)
7. [SSRF & Path Traversal Prevention](#ssrf--path-traversal-prevention)
8. [Request/Response Security](#requestresponse-security)
9. [Logging & Audit](#logging--audit)
10. [Headers & Transport Security](#headers--transport-security)
11. [Reusable Security Utilities](#reusable-security-utilities)

---

## Core Security Principles

### 1. Defense in Depth

- Multiple layers of security controls (auth → validation → rate limiting → output sanitization)
- No single failure point exposes the system
- Security is distributed across middleware, utilities, and provider logic

### 2. Fail Secure

- Default to denying access; explicitly grant permissions
- Return generic error messages that don't leak system information
- Log detailed errors internally but show sanitized messages to clients

### 3. Principle of Least Privilege

- Each endpoint, provider, and utility has minimal required permissions
- Auth scopes/claims are explicitly checked, not assumed
- Providers only expose endpoints they implement; unknown endpoints are hidden

### 4. Security by Default

- Security features are enabled by default (auth, rate limiting, CORS)
- Operators must explicitly disable them with documented tradeoffs
- Sensitive operations require additional confirmation (e.g., token validation)

---

## Error Handling & Information Disclosure

### ✅ STANDARD: Sanitized Error Responses

**Rule:** Never expose internal error details, stack traces, file paths, or sensitive configuration to clients.

#### Implementation Pattern

```python
from logging import Logger
from fastapi.responses import JSONResponse
from drunk_ai_proxy.utils.security import sanitize_error_response
from drunk_ai_proxy.utils.logging_config import setup_logging

class MyProvider:
    def __init__(self):
        self._logger: Logger = setup_logging(__name__)
    
    async def process_request(self, data: dict) -> JSONResponse:
        """Process user request with safe error handling."""
        try:
            result = await self._execute(data)
            return JSONResponse({"result": result})
        except ValueError as e:
            # Log full exception type privately
            self._logger.warning("Validation error: %s", type(e).__name__)
            # Return generic message to client
            return sanitize_error_response(
                user_message="Invalid input provided",
                status_code=400,
                log_context="process_request validation"
            )
        except Exception as e:
            # Unexpected errors
            self._logger.error("Unexpected error: %s", type(e).__name__)
            return sanitize_error_response(
                user_message="An error occurred while processing your request",
                status_code=500,
                log_context="process_request execution"
            )
```

#### Key Rules

1. **Log only exception type**: Use `type(e).__name__`, never `str(e)` which may contain secrets
2. **Distinguish expected vs unexpected errors**:
   - **Expected errors** (validation, auth): Return 4xx with generic message
   - **Unexpected errors** (bugs, crashes): Return 5xx with generic message
3. **Never log**:
   - File paths
   - API keys, tokens, connection strings
   - Database query details
   - Internal IP addresses or hostnames
   - User data contained in requests
4. **May log** (after sanitization):
   - Exception type name
   - Operation context (method name, endpoint)
   - Request ID or correlation ID
   - Request size or type
   - HTTP status code

### ✅ STANDARD: Actionable Errors

**Rule:** For errors that genuinely help users fix the issue, return specific (but safe) messages.

#### User-Actionable Errors

These errors provide helpful guidance and are safe to expose:

```python
from drunk_ai_proxy.utils.security import is_user_actionable_error, get_actionable_message

# Examples that are actionable:
# - "Model ID format invalid. Expected 'provider_model_name'"
# - "Missing required field 'messages' in request"
# - "Rate limit exceeded. Try again in 60 seconds"
# - "Authentication required. Provide Authorization header"

def handle_model_validation(model_id: str | None) -> JSONResponse | None:
    """Validate model_id, returning actionable error if invalid."""
    if not model_id:
        return JSONResponse(
            {"error": "Model ID required. Use format: 'provider_model'"},
            status_code=400
        )
    return None
```

#### Non-Actionable Errors (Must Be Generic)

These must NEVER be exposed to users:

```python
# ❌ BAD - leaks system details
except DatabaseError as e:
    return JSONResponse({"error": str(e)})  # Exposes DB driver, connection info

# ✅ GOOD - generic message
except DatabaseError as e:
    self._logger.error("DB error: %s", type(e).__name__)
    return JSONResponse(
        {"error": "An error occurred while processing your request"},
        status_code=500
    )

# ❌ BAD - leaks file paths
except FileNotFoundError as e:
    return JSONResponse({"error": str(e)})  # Shows absolute path

# ✅ GOOD - generic message
except FileNotFoundError as e:
    self._logger.error("File error: %s", type(e).__name__)
    return JSONResponse(
        {"error": "Resource not found"},
        status_code=404
    )
```

---

## Authentication & Authorization

### ✅ STANDARD: Token Validation

**Rule:** All protected endpoints must validate auth tokens and check claims/scopes.

#### Implementation Pattern

```python
from fastapi import FastAPI, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastmcp.server.auth import AuthProvider
from fastapi.responses import JSONResponse

class ProtectedProvider:
    def __init__(self, auth: AuthProvider | None):
        self._auth = auth
        self._fastapi_app = FastAPI()
        
        # Conditionally add auth dependencies
        self.dependencies = []
        if self._auth:
            self.dependencies = [Depends(self._verify_token)]
        
        self._fastapi_app.add_api_route(
            "/protected-endpoint",
            self._protected_endpoint,
            methods=["POST"],
            dependencies=self.dependencies  # Apply auth if enabled
        )
    
    async def _verify_token(
        self,
        credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False))
    ) -> dict:
        """Verify and extract claims from token."""
        if not credentials:
            return JSONResponse(
                {"error": "Authorization required"},
                status_code=401
            )
        
        # Delegate to auth provider
        result = await self._auth.verify_token(credentials.credentials)
        if result is None or (not result.claims and not result.scopes):
            return JSONResponse(
                {"error": "Invalid token"},
                status_code=401
            )
        
        return result
    
    async def _protected_endpoint(self, request: Request) -> JSONResponse:
        """Example protected endpoint."""
        # Access auth context if needed
        # (Depends injects the result of _verify_token)
        return JSONResponse({"success": True})
```

#### Key Rules

1. **Conditionally add auth**: Only add auth dependencies if `auth` is enabled
2. **Check claims/scopes**: Don't assume token is valid; verify claims
3. **Return 401 for auth failures**: Distinguish from 403 (forbidden after auth)
4. **Never log tokens**: Even truncated tokens can be exploited
5. **Validate token format**: Require at minimum "Bearer {token}" scheme

### ✅ STANDARD: Scope Validation

**Rule:** Sensitive operations require additional scope/permission checks.

```python
async def _admin_endpoint(self, request: Request) -> JSONResponse:
    """Endpoint requiring admin scope."""
    # Assuming claims extracted and available via context
    claims = request.state.claims  # Set by auth middleware
    
    if "admin" not in claims.get("scopes", []):
        return JSONResponse(
            {"error": "Insufficient permissions"},
            status_code=403
        )
    
    # Proceed with admin operation
    return JSONResponse({"admin_data": "..."})
```

---

## Input Validation

### ✅ STANDARD: Pydantic Models for All Inputs

**Rule:** All request bodies and form data must be validated with Pydantic models.

#### Implementation Pattern

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List

class ChatRequestModel(BaseModel):
    """Validated chat completion request."""
    
    model: str = Field(..., min_length=1, max_length=255, description="Model ID")
    messages: List[dict] = Field(..., min_items=1, max_items=100, description="Messages")
    temperature: Optional[float] = Field(default=1.0, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=4096)
    
    @validator('model')
    def validate_model_format(cls, v):
        """Ensure model follows 'provider_model' format."""
        if "_" not in v:
            raise ValueError("Model must be in format 'provider_model'")
        return v


class MyProvider:
    async def _chat_endpoint(self, request: ChatRequestModel) -> JSONResponse:
        """FastAPI auto-validates input via Pydantic."""
        # request.model and other fields are guaranteed valid
        result = await self._process_chat(request.model, request.messages)
        return JSONResponse({"result": result})
```

#### Key Rules

1. **Always use Pydantic**: Never parse raw JSON manually
2. **Set field constraints**: min/max length, ranges, patterns
3. **Validate boundaries**: Use `Field(ge=..., le=...)` for numeric limits
4. **Custom validators**: Add `@validator` for complex logic
5. **Fail fast**: Pydantic errors return 422 (Unprocessable Entity) automatically

### ✅ STANDARD: Query Parameter Validation

**Rule:** Query parameters must also be validated.

```python
from fastapi import Query

class MyProvider:
    async def _list_endpoint(
        self,
        limit: int = Query(10, ge=1, le=100),
        offset: int = Query(0, ge=0),
        search: Optional[str] = Query(None, max_length=255)
    ) -> JSONResponse:
        """List endpoint with validated query params."""
        # limit, offset, search guaranteed valid by FastAPI
        return JSONResponse({"items": []})
```

### ✅ STANDARD: File Upload Validation

**Rule:** File uploads must validate name, size, and type.

```python
from fastapi import UploadFile, File
from drunk_ai_proxy.utils.security import validate_file_upload

async def _upload_endpoint(
    self,
    file: UploadFile = File(...)
) -> JSONResponse:
    """Handle file upload with validation."""
    # Validate file before processing
    error = await validate_file_upload(
        file,
        allowed_extensions=[".md", ".txt", ".yaml", ".json"],
        max_size_mb=10,
        allowed_mimetypes=["text/plain", "application/json"]
    )
    
    if error:
        return error  # JSONResponse with validation error
    
    # Process validated file
    content = await file.read()
    return JSONResponse({"uploaded": file.filename})
```

---

## Rate Limiting & DoS Prevention

### ✅ STANDARD: Global Rate Limiting

**Rule:** All public endpoints must have rate limiting by client IP.

#### Implementation

```python
# In middleware_provider.py (already implemented)
from drunk_ai_proxy.app.middleware_provider import get_middlewares

# Enabled via env vars:
# RATE_LIMIT_ENABLED=true
# RATE_LIMIT_REQUESTS=100
# RATE_LIMIT_WINDOW_SECONDS=60
```

#### Key Rules

1. **Rate limit by IP**: Extract real IP via `X-Forwarded-For` header
2. **Fixed-window algorithm**: Simpler and more predictable than sliding
3. **Return 429 status**: Include `Retry-After` header
4. **Separate public/private**: Different limits for public vs authenticated endpoints

### ✅ STANDARD: Request Size Limits

**Rule:** Limit request body size to prevent memory exhaustion.

```python
from drunk_ai_proxy.app.middleware_provider import RequestSizeLimitMiddleware

# Add to middleware stack:
middlewares = [
    Middleware(
        RequestSizeLimitMiddleware,
        max_size_bytes=10 * 1024 * 1024  # 10 MB limit
    )
]
```

### ✅ STANDARD: Timeout Protection

**Rule:** Long-running operations must have timeouts.

```python
import asyncio
from http import HTTPStatus

async def _chat_completions_endpoint(self, request: ChatRequestModel) -> JSONResponse:
    """Chat endpoint with timeout protection."""
    try:
        # Timeout at 30 seconds
        result = await asyncio.wait_for(
            self._stream_chat(request),
            timeout=30.0
        )
        return JSONResponse({"choices": result})
    except asyncio.TimeoutError:
        return JSONResponse(
            {"error": "Request timed out. Try with shorter messages or higher temperature."},
            status_code=504  # Gateway Timeout
        )
```

---

## CORS & Cross-Origin Security

### ✅ STANDARD: Explicit CORS Configuration

**Rule:** CORS must be explicitly configured; never use `allow_origins=["*"]` with credentials.

#### Implementation

```python
# In middleware_provider.py (already implemented)
from drunk_ai_proxy.app.middleware_provider import _create_cors_middleware

# Configuration via env vars:
# CORS_ALLOW_ORIGINS=https://example.com,https://app.example.com
# CORS_ALLOW_METHODS=GET,POST,PUT,DELETE
# CORS_ALLOW_HEADERS=Content-Type,Authorization
# CORS_ALLOW_CREDENTIALS=true
# CORS_MAX_AGE=3600
```

#### Key Rules

1. **Never use `["*"]` with credentials**: Either `["*"]` without credentials, or explicit origins with credentials
2. **Explicit methods**: Only allow HTTP methods actually used
3. **Explicit headers**: Only allow headers clients actually send
4. **Max-Age for preflight**: Cache preflight responses to reduce overhead
5. **Expose headers carefully**: Only expose headers clients need

---

## SSRF & Path Traversal Prevention

### ✅ STANDARD: URL Validation

**Rule:** All URLs from user input must be validated to prevent SSRF attacks.

```python
from drunk_ai_proxy.utils.security import validate_url

def validate_and_download(self, url: str) -> bytes | JSONResponse:
    """Download file from URL with SSRF protection."""
    # Validate before fetching
    error = validate_url(
        url,
        allowed_schemes=["https"],  # Whitelist HTTPS only
        blocked_hosts=["localhost", "127.0.0.1", "169.254.169.254"],  # Block metadata endpoints
        require_public_ip=True  # Reject private IP ranges
    )
    
    if error:
        return error  # JSONResponse with validation error
    
    # Safe to download
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.content
```

### ✅ STANDARD: Path Traversal Prevention

**Rule:** File paths must be validated to prevent directory traversal attacks.

```python
from pathlib import Path
from drunk_ai_proxy.utils.security import safe_path_join

def read_config_file(self, filename: str) -> str | JSONResponse:
    """Read config file with path traversal protection."""
    config_dir = Path("/app/data/config")
    
    # Safely join and validate path is within config_dir
    safe_path = safe_path_join(config_dir, filename)
    if not safe_path:
        return JSONResponse(
            {"error": "Invalid file path"},
            status_code=400
        )
    
    # Read file (now guaranteed to be within config_dir)
    return safe_path.read_text()
```

#### Key Rules

1. **Use `safe_path_join()`**: Never concatenate paths manually
2. **Resolve realpath**: Use `Path.resolve()` to handle symlinks
3. **Check parent**: Verify final path starts with parent directory
4. **Whitelist characters**: Allow only alphanumeric, `-`, `_`, `.`, `/`

---

## Request/Response Security

### ✅ STANDARD: Input Size Validation

**Rule:** Validate input dimensions and content size before processing.

```python
async def _chat_completions_endpoint(self, request: ChatRequestModel) -> JSONResponse:
    """Validate input constraints."""
    # Validate message count
    if len(request.messages) > 100:
        return JSONResponse(
            {"error": "Maximum 100 messages allowed"},
            status_code=400
        )
    
    # Validate total content size
    total_size = sum(len(m.get("content", "")) for m in request.messages)
    if total_size > 1_000_000:  # 1 MB content limit
        return JSONResponse(
            {"error": "Total message content exceeds 1 MB"},
            status_code=413  # Payload Too Large
        )
    
    return JSONResponse({"result": "OK"})
```

### ✅ STANDARD: Output Encoding

**Rule:** All output must be properly encoded and escaped.

```python
from pydantic import BaseModel

class ResponseModel(BaseModel):
    """Response is auto-validated by Pydantic."""
    message: str  # Auto-escaped for JSON
    status: str   # Auto-escaped for JSON

# FastAPI auto-encodes via json.dumps(...) which handles escaping
```

### ✅ STANDARD: Content-Type Validation

**Rule:** Validate Content-Type header matches expected format.

```python
from fastapi import Header
from typing import Optional

async def _process_request(
    self,
    request: ChatRequestModel,
    content_type: Optional[str] = Header(None)
) -> JSONResponse:
    """Validate Content-Type is JSON."""
    if content_type and "application/json" not in content_type:
        return JSONResponse(
            {"error": "Content-Type must be application/json"},
            status_code=415  # Unsupported Media Type
        )
    return JSONResponse({"success": True})
```

---

## Logging & Audit

### ✅ STANDARD: Security Event Logging

**Rule:** All security-relevant events must be logged for audit trails.

#### Events to Log

1. **Authentication failures**: Invalid token, auth bypass attempts
2. **Authorization failures**: Insufficient scopes, forbidden resources
3. **Rate limit violations**: Repeated 429 responses from same IP
4. **Invalid input**: Validation errors, malformed requests
5. **Resource access**: Who accessed what (user, resource, timestamp)
6. **Configuration changes**: If applicable, admin operations

#### Implementation Pattern

```python
from logging import Logger
from drunk_ai_proxy.utils.security import audit_log
from drunk_ai_proxy.utils.logging_config import setup_logging

class MyProvider:
    def __init__(self):
        self._logger: Logger = setup_logging(__name__)
    
    async def _protected_endpoint(self, request: Request, user_id: str) -> JSONResponse:
        """Log security-relevant events."""
        try:
            # Log successful access
            audit_log(
                self._logger,
                event="resource_accessed",
                user_id=user_id,
                resource="/protected-endpoint",
                status="success"
            )
            
            result = await self._process()
            return JSONResponse({"result": result})
        
        except PermissionError:
            # Log authorization failure
            audit_log(
                self._logger,
                event="authorization_failed",
                user_id=user_id,
                resource="/protected-endpoint",
                reason="insufficient_scopes",
                status="denied"
            )
            return JSONResponse({"error": "Access denied"}, status_code=403)
        
        except Exception as e:
            # Log unexpected errors (but don't expose details)
            audit_log(
                self._logger,
                event="error",
                resource="/protected-endpoint",
                error_type=type(e).__name__,
                status="failed"
            )
            return JSONResponse(
                {"error": "An error occurred"},
                status_code=500
            )
```

### ✅ STANDARD: Secrets Masking

**Rule:** Never log secrets; mask sensitive values in logs.

```python
from drunk_ai_proxy.utils.security import mask_sensitive_value

class ConfigProvider:
    def log_config(self, config: dict) -> None:
        """Log configuration while masking secrets."""
        safe_config = {
            k: mask_sensitive_value(v, key=k)
            for k, v in config.items()
        }
        self._logger.info("Config loaded: %s", safe_config)

# mask_sensitive_value() checks key names:
# If key contains "token", "key", "secret", "password" → show last 4 chars
# Otherwise → show full value
```

---

## Headers & Transport Security

### ✅ STANDARD: Security Headers

**Rule:** Add security headers to all responses.

```python
from drunk_ai_proxy.app.middleware_provider import SecurityHeadersMiddleware

# Add to middleware stack:
middlewares = [
    Middleware(
        SecurityHeadersMiddleware,
        headers={
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        }
    )
]
```

#### Headers to Add

| Header | Value | Purpose |
|---|---|---|
| `X-Content-Type-Options` | `nosniff` | Prevent MIME sniffing attacks |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `X-XSS-Protection` | `1; mode=block` | Enable XSS filter |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Force HTTPS |
| `Content-Security-Policy` | Restrictive policy | Prevent injection attacks |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limit referrer leakage |
| `Permissions-Policy` | Camera, microphone deny | Limit API access |

### ✅ STANDARD: HTTPS Enforcement

**Rule:** All production deployments must use HTTPS only.

```python
# In env vars:
FORCE_HTTPS=true  # Redirect HTTP → HTTPS
HTTPS_ONLY=true   # Return 403 for HTTP requests
```

---

## Reusable Security Utilities

### Create Security Module

All security utilities are importable from `drunk_ai_proxy.utils.security`:

```python
from drunk_ai_proxy.utils.security import (
    sanitize_error_response,
    is_user_actionable_error,
    get_actionable_message,
    validate_url,
    validate_file_upload,
    safe_path_join,
    mask_sensitive_value,
    audit_log,
)
```

Module location: `src/drunk_ai_proxy/drunk_ai_proxy/utils/security.py`

---

## Security Checklist for New Features

When adding new endpoints, providers, or features, verify:

- [ ] **Authentication**: Protected endpoints validate auth tokens
- [ ] **Authorization**: Endpoints check claims/scopes for sensitive operations
- [ ] **Input validation**: All inputs validated with Pydantic or custom validators
- [ ] **Error handling**: Errors sanitized; full details logged privately
- [ ] **Rate limiting**: Public endpoints have rate limits
- [ ] **Logging**: Security events logged for audit
- [ ] **SSRF prevention**: URLs validated if from user input
- [ ] **Path traversal**: File paths validated with `safe_path_join()`
- [ ] **Output encoding**: Responses auto-encoded via JSON
- [ ] **Headers**: Security headers present in responses
- [ ] **Testing**: Security-specific test cases included

---

## Implementation Phases

### Phase 1: Core Utilities (Current)
- ✅ Create `utils/security.py` with reusable functions
- ✅ Update error handling across all providers
- ✅ Add security headers middleware
- ✅ Add request size limit middleware

### Phase 2: Provider Updates
- Update all FastAPI providers to use security utilities
- Add input validation where missing
- Extend audit logging
- Add HTTPS enforcement option

### Phase 3: Testing & Hardening
- Add security-specific test suite
- Penetration testing simulation
- Dependency vulnerability scan
- Security audit of all endpoints

### Phase 4: Monitoring & Incident Response
- Add security event alerts
- Create incident response procedures
- Add metrics for security violations
- Document security escalation paths

---

## References

- [OWASP Top 10 2023](https://owasp.org/www-project-top-ten/)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

---

**Approval Required For:**
- Any deviation from error sanitization standards
- Disabling rate limiting
- Disabling authentication
- Adding new authentication mechanisms
- Changes to CORS configuration

---

**Last Review:** March 2026  
**Next Review:** September 2026
