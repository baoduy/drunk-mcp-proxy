"""Security Integration Guide for Drunk MCP Proxy

This guide provides step-by-step instructions for integrating security utilities
and middleware into FastAPI providers and FastMCP resources.
"""

# Security Integration Guide

## Overview

The security framework consists of three components:

1. **Security Standards** (`docs/security/SECURITY_STANDARDS.md`) - Reference standards
2. **Security Utilities** (`src/drunk_ai_proxy/utils/security.py`) - 11 reusable functions
3. **Security Middleware** (`src/drunk_ai_proxy/app/security_headers_middleware.py`) - HTTP security headers

## Quick Start

### 1. Add Security Headers Middleware to Your App

In `src/app/server.py` or your Starlette app factory:

```python
from drunk_ai_proxy.app.security_headers_middleware import (
    SecurityHeadersMiddleware,
    RequestSizeLimitMiddleware,
)

# In your app setup:
app.add_middleware(RequestSizeLimitMiddleware, max_size_bytes=10_242_880)  # 10 MB
app.add_middleware(SecurityHeadersMiddleware)
```

This adds standard security headers to all responses automatically.

### 2. Use Error Sanitization in FastAPI Endpoints

**Problem**: Raw exception messages expose internal details to clients.

**Solution**: Use `sanitize_error_response()` to return safe error messages.

```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from drunk_ai_proxy.utils.security import (
    sanitize_error_response,
    is_user_actionable_error,
    get_actionable_message,
)

router = APIRouter()

@router.post("/api/process")
async def process_endpoint(request: dict) -> dict:
    """Process request with error sanitization.
    
    Example error handling that protects internal details while
    providing useful feedback to users.
    """
    try:
        # Your business logic here
        result = await process_business_logic(request)
        return result
    except ValueError as e:
        # Actionable errors (format, required fields) can be shown to users
        if is_user_actionable_error(str(e)):
            logger.warning("Validation error: %s", type(e).__name__)
            return sanitize_error_response(
                user_message=get_actionable_message(e),
                status_code=400,
                log_context="process_endpoint"
            )
        else:
            # Non-actionable errors are hidden
            logger.error("Processing error: %s", type(e).__name__)
            return sanitize_error_response(
                user_message="An error occurred while processing your request",
                status_code=500,
                log_context="process_endpoint"
            )
```

### 3. Validate URLs Before Fetching (SSRF Prevention)

**Problem**: Accepting arbitrary URLs enables Server-Side Request Forgery attacks.

**Solution**: Validate URLs against whitelist/blacklist before using them.

```python
from drunk_ai_proxy.utils.security import validate_url

@router.post("/api/fetch")
async def fetch_external_data(url: str) -> dict:
    """Fetch data from external URL with SSRF prevention.
    
    Only allows HTTPS URLs to public IPs (blocks localhost, 10.x.x.x, etc).
    """
    # Validate URL before making request
    error = validate_url(
        url,
        allowed_schemes=["https"],  # Only HTTPS
        require_public_ip=True,      # Block private IPs
        blocked_hosts=["internal-api.local", "admin.example.com"],
    )
    
    if error:
        return error  # Returns 400 JSONResponse with error message
    
    # URL is validated as safe
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

### 4. Prevent Path Traversal Attacks

**Problem**: Using user-supplied filenames without validation allows access outside intended directory.

**Solution**: Use `safe_path_join()` to construct file paths safely.

```python
from pathlib import Path
from drunk_ai_proxy.utils.security import safe_path_join
from fastapi import UploadFile

@router.post("/api/upload")
async def upload_file(filename: str, file: UploadFile) -> dict:
    """Upload file safely without path traversal.
    
    Blocks attempts to use ../../../etc/passwd or /etc/passwd.
    """
    base_dir = Path("/app/uploads")
    
    # Validate path - returns None if unsafe
    safe_path = safe_path_join(base_dir, filename)
    if not safe_path:
        return sanitize_error_response(
            user_message="Invalid filename",
            status_code=400
        )
    
    # Safe to write to the path
    with open(safe_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    return {"status": "ok", "path": safe_path.name}
```

### 5. Validate File Uploads

**Problem**: Accepting any file type/size enables DOS and malware upload.

**Solution**: Validate uploads with extension/MIME type/size checks.

```python
from drunk_ai_proxy.utils.security import validate_file_upload

@router.post("/api/import-config")
async def import_config(file: UploadFile) -> dict:
    """Import configuration file with validation.
    
    Only accepts .yaml files under 1MB to prevent abuse.
    """
    error = validate_file_upload(
        file,
        allowed_extensions=[".yaml", ".yml"],
        allowed_mimetypes=["application/x-yaml", "text/yaml"],
        max_size_mb=1,
    )
    
    if error:
        return error  # Returns 400 JSONResponse with error message
    
    # File is validated as safe
    content = await file.read()
    config = yaml.safe_load(content)
    return {"status": "ok", "config": config}
```

### 6. Mask Sensitive Values in Logs

**Problem**: Logging API keys, tokens, or passwords exposes sensitive data in log files.

**Solution**: Use `mask_sensitive_value()` to show only last 4 characters.

```python
from drunk_ai_proxy.utils.security import mask_sensitive_value

class ApiClient:
    """API client with safe logging."""
    
    def __init__(self, api_key: str) -> None:
        """Initialize client with API key.
        
        Safe: Logs only last 4 characters of key.
        """
        self._logger = setup_logging(__name__)
        self._api_key = api_key
        
        # Safe: Shows ...key_suffix, not full key
        masked = mask_sensitive_value(api_key, key="api_key")
        self._logger.info("API client initialized with %s", masked)
    
    def make_request(self, url: str) -> dict:
        """Make authenticated request."""
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "X-Custom-Token": get_session_token(),
        }
        
        # When logging headers (for debugging), mask sensitive values
        safe_headers = {
            k: mask_sensitive_value(v, key=k)
            for k, v in headers.items()
        }
        self._logger.debug("Request headers: %s", safe_headers)
        
        return requests.get(url, headers=headers).json()
```

### 7. Log Security Events with Audit Trail

**Problem**: Security events not tracked, making incident investigation difficult.

**Solution**: Use `audit_log()` for structured security event logging.

```python
from drunk_ai_proxy.utils.security import audit_log

class AuthenticationService:
    """Authentication with audit logging."""
    
    async def login(self, username: str, password: str) -> dict:
        """Authenticate user and log event."""
        try:
            user = await self._validate_credentials(username, password)
            
            # Log successful authentication
            audit_log(
                logger=self._logger,
                event="user_login",
                status="success",
                user_id=user.id,
                details={"method": "password", "ip_address": get_client_ip()},
            )
            
            return {"token": create_token(user.id)}
        
        except InvalidCredentialsError:
            # Log failed authentication
            audit_log(
                logger=self._logger,
                event="user_login",
                status="failure",
                user_id=username,
                details={"reason": "invalid_credentials", "ip_address": get_client_ip()},
            )
            
            return sanitize_error_response(
                user_message="Invalid username or password",
                status_code=401
            )
```

### 8. Validate Request Size

**Problem**: Large requests can exhaust memory and cause DOS.

**Solution**: Check Content-Length header before processing.

```python
from drunk_ai_proxy.utils.security import validate_request_size

@router.post("/api/batch-process")
async def batch_process(request: Request) -> dict:
    """Process batch with size limits."""
    # Validate request size (100MB limit)
    content_length = request.headers.get("content-length")
    error = validate_request_size(
        content_length,
        max_bytes=100 * 1024 * 1024,  # 100 MB
    )
    
    if error:
        return error  # Returns 413 if too large
    
    # Safe to process
    body = await request.json()
    return process_batch(body)
```

### 9. Validate Content-Type

**Problem**: Accepting wrong content types can cause parsing errors or security issues.

**Solution**: Validate Content-Type before processing request body.

```python
from drunk_ai_proxy.utils.security import validate_content_type

@router.post("/api/config", consumes=["application/json", "application/yaml"])
async def update_config(request: Request) -> dict:
    """Update configuration with content-type validation."""
    content_type = request.headers.get("content-type", "")
    
    # Validate expected types
    error = validate_content_type(
        content_type,
        expected_types=["application/json", "application/x-yaml"],
    )
    
    if error:
        return error  # Returns 415 if wrong type
    
    # Parse based on content type
    if "json" in content_type:
        data = await request.json()
    elif "yaml" in content_type:
        body = await request.body()
        data = yaml.safe_load(body)
    
    return {"status": "updated"}
```

### 10. Handle Pydantic Validation Errors

**Problem**: Raw Pydantic errors expose dataclass field names and structure.

**Solution**: Convert errors to user-friendly JSON responses.

```python
from fastapi import APIRouter
from pydantic import BaseModel
from drunk_ai_proxy.utils.security import handle_validation_error

class ConfigModel(BaseModel):
    """Configuration with validation."""
    timeout: int  # Must be positive integer
    endpoint: str  # Must not be empty

@router.post("/api/configure")
async def configure(config: ConfigModel) -> dict:
    """Configure with validation error handling.
    
    Pydantic automatically validates the config parameter.
    If validation fails, FastAPI catches the ValidationError
    and converts it using our security-aware handler.
    """
    # If config validation fails, FastAPI's exception handler
    # can use handle_validation_error() to sanitize the response
    return {"status": "configured", "config": config.dict()}
```

To wire up custom validation error handling globally:

```python
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from drunk_ai_proxy.utils.security import handle_validation_error

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Handle validation errors with sanitization."""
    return handle_validation_error(exc)
```

## Integration Checklist

Before deploying a new provider, ensure:

- ✅ Security headers middleware is added to the app
- ✅ All user-facing error messages use `sanitize_error_response()`
- ✅ All external URLs validated with `validate_url()`
- ✅ All file paths created with `safe_path_join()`
- ✅ All file uploads validated with `validate_file_upload()`
- ✅ Sensitive values in logs masked with `mask_sensitive_value()`
- ✅ Critical events logged with `audit_log()`
- ✅ Request size checked with `validate_request_size()`
- ✅ Content-Type validated with `validate_content_type()`
- ✅ Pydantic errors handled with `handle_validation_error()`

## Testing Security Features

All security utilities have comprehensive test coverage:

```bash
# Run security tests
python -m pytest tests/test_security.py tests/test_security_headers_middleware.py -v

# Run with coverage
python -m pytest tests/test_security* --cov=src/drunk_ai_proxy/utils/security --cov=src/drunk_ai_proxy/app/security_headers_middleware
```

## Performance Considerations

- **URL Validation**: Uses `ipaddress` module (minimal overhead)
- **Path Traversal Check**: Uses `Path.resolve()` (filesystem call, but only on user input)
- **Content-Type Parsing**: Simple string comparison
- **Secrets Masking**: O(n) string slicing (negligible)
- **Audit Logging**: Async-safe JSON serialization

All utilities are production-ready with sub-millisecond overhead for typical inputs.

## References

- [OWASP Top 10](https://owasp.org/Top10/) - Web application security risks
- [Security Standards](../docs/security/SECURITY_STANDARDS.md) - Project security standards
- [Security Utilities](../src/drunk_ai_proxy/utils/security.py) - API reference
- [Security Middleware](../src/drunk_ai_proxy/app/security_headers_middleware.py) - Middleware reference

## Questions?

Refer to specific sections:
- **Error handling**: See `sanitize_error_response()` docstring
- **URL validation**: See `validate_url()` docstring  
- **Path safety**: See `safe_path_join()` docstring
- **File uploads**: See `validate_file_upload()` docstring
- **Logging**: See `audit_log()` and `mask_sensitive_value()` docstrings
