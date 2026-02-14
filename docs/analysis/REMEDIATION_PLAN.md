# MCP Proxy Server - Remediation Plan & Action Items

**Document Purpose:** Specific, actionable remediation for identified gaps  
**Last Updated:** February 13, 2026  
**Total Issues to Address:** 19 (3 Critical, 5 High, 6 Medium, 5 Low)

---

## IMMEDIATE ACTION ITEMS (Complete This Week)

### ACTION #1: Add Missing Dependencies ⏱️ 5 minutes

**Issue:** pytest and pytest-cov missing from requirements.txt (blocks Phase 2)

**File:** `requirements.txt`

**Current State:**

```
fastmcp>=3.0.0rc1
jsonschema>=4.0.0
uvicorn>=0.27.0
...
botocore>=1.35.0
```

**Required Change:**

```
Add to the end of requirements.txt:
pytest>=7.0.0
pytest-cov>=4.0.0
```

**Verification:**

```bash
pip install -r requirements.txt
pytest --version
```

**Owner:** Backend Lead  
**Dependency:** None  
**Blocks:** Phase 2 (Testing) - All 20 items

---

### ACTION #2: Fix Docker Path Inconsistencies ⏱️ 1-2 hours

**Issue:** docker-compose.yml uses `/app` but Dockerfile uses `/mcp_proxy` (causes runtime failures)

**Files Affected:**

1. `docker-compose.yml` (lines 8-9, 20, 22)
2. `Dockerfile` (lines 50, 54, 55, 66, 68)

**Current Inconsistencies:**

| Path       | Dockerfile      | docker-compose | Issue      |
|------------|-----------------|----------------|------------|
| Work Dir   | /mcp_proxy      | /app           | ❌ MISMATCH |
| Config     | /mcp_proxy/data | /app/data      | ❌ MISMATCH |
| PYTHONPATH | /mcp_proxy      | /app/src       | ❌ MISMATCH |

**Recommended Fix:** Standardize ALL paths to `/mcp_proxy` (matches Dockerfile)

**Changes Needed:**

**File: docker-compose.yml**

Change line 8:

```yaml
# OLD:
volumes:
  - ./data:/app/data

# NEW:
volumes:
  - ./data:/mcp_proxy/data
```

Change line 20:

```yaml
# OLD:
- FASTMCP_CONFIG_DIR=/app/data

# NEW:
- FASTMCP_CONFIG_DIR=/mcp_proxy/data
```

Change line 22:

```yaml
# OLD:
- PYTHONPATH=/app/src

# NEW:
- PYTHONPATH=/mcp_proxy
```

**Verification:**

```bash
docker-compose build
docker-compose up
curl http://localhost:9123/health
```

**Owner:** DevOps Lead  
**Dependency:** None  
**Impact:** Prevents container startup failures

---

### ACTION #3: Fix Code Quality Issues ⏱️ 1 hour

#### 3a: Rename cors_middleware.py (30 minutes)

**Issue:** File named `cros_middleware.py` instead of `cors_middleware.py` (typo)

**Files to Modify:**

1. Rename: `src/app/middleware/cros_middleware.py` → `src/app/middleware/cors_middleware.py`
2. Update import: `src/app/server.py` (line with the import)

**Current Import (in app/server.py):**

```python
from .middleware import build_cors_middleware
```

(This should still work if middleware.__init__.py exports correctly)

**Verification:**

```bash
python -m py_compile src/app/middleware/cors_middleware.py
python -m src.main
```

**Owner:** Backend Lead  
**Dependency:** None

#### 3b: Add Missing Docstring (30 minutes)

**Issue:** `_coerce_value()` function in auth.py missing docstring (lines 152-186)

**File:** `src/app/auth.py`

**Current State (line 152):**

```python
def _coerce_value(param_name: str, raw_value: str) -> Union[bool, list[str], str]:
    # Missing docstring here
    if param_name.lower().endswith("_urls"):
        return [url.strip() for url in raw_value.split(",") if url.strip()]
    ...
```

**Required Docstring to Add:**

```python
def _coerce_value(param_name: str, raw_value: str) -> Union[bool, list[str], str]:
    """
    Coerce environment variable string value to appropriate Python type.

    Applies type conversion based on parameter naming patterns:
    - Parameters ending with "_urls" are converted to list of strings
    - Parameters containing "flag" are converted to boolean
    - Other parameters remain as strings

    Args:
        param_name: Parameter name (used to infer type)
        raw_value: Raw string value from environment variable

    Returns:
        Coerced value (bool, list[str], or str) based on parameter name pattern

    Examples:
        _coerce_value("auth_urls", "http://a.com, http://b.com") 
        -> ["http://a.com", "http://b.com"]
        
        _coerce_value("use_flag", "true") -> True
        
        _coerce_value("token", "secret123") -> "secret123"
    """
```

**Verification:**

```bash
python -c "from src.app.auth import _coerce_value; help(_coerce_value)"
```

**Owner:** Backend Lead  
**Dependency:** None

---

## SHORT-TERM ACTIONS (Complete Weeks 1-2)

### ACTION #4: Set Up Testing Framework ⏱️ 4 hours

**Issue:** No testing framework set up (Phase 2 at 0%)

**Deliverables:**

Create directory structure:

```
tests/
├── __init__.py
├── conftest.py                    # pytest fixtures & config
├── test_env.py                    # 8 tests
├── test_validation.py             # 12 tests
├── test_cors_middleware.py        # 10 tests
├── test_auth.py                   # 15 tests
├── test_static_proxies.py         # 18 tests
├── test_server.py                 # 20 tests
└── integration/
    └── test_proxy_flow.py         # Integration tests
```

**File: tests/conftest.py** (3 hours)

```python
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import json


@pytest.fixture
def config_dir():
    """Create temporary config directory with sample configs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create sample stock.mcp.json
        stock_config = {
            "mcpServers": {
                "stock": {
                    "command": "python",
                    "args": ["server.py"]
                }
            }
        }
        with open(f"{tmpdir}/stock.mcp.json", "w") as f:
            json.dump(stock_config, f)
        yield tmpdir


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    return Mock()


@pytest.fixture
def mock_fastmcp():
    """Mock FastMCP server."""
    return Mock()

# Add more fixtures as needed for auth, CORS, etc.
```

**Coverage Target:** 80%+ of code

**Owner:** QA Lead  
**Dependency:** Action #1 (pytest installation)  
**Blocks:** Beta testing, production deployment

---

### ACTION #5: Implement Unit Tests ⏱️ 36 hours

**Phase 1: Core Modules (20 hours)**

**test_env.py** (1.5 hours, 8 tests)

```python
def test_config_dir_default():
    """Test CONFIG_DIR defaults to 'data'."""


def test_log_level_valid():
    """Test LOG_LEVEL correctly parses from env."""


def test_port_validation():
    """Test PORT validates and defaults to 9123."""


def test_server_name_stripping():
    """Test SERVER_NAME whitespace trimming."""

# ... 4 more tests
```

**test_validation.py** (3 hours, 12 tests)

```python
def test_load_schema_exists():
    """Test schema loading from valid path."""


def test_load_schema_missing():
    """Test graceful handling of missing schema."""


def test_validate_mcp_config_valid():
    """Test validation passes for valid config."""


def test_validate_mcp_config_invalid():
    """Test validation fails for invalid config."""

# ... 8 more tests
```

**test_cors_middleware.py** (1.5 hours, 10 tests)

```python
def test_build_cors_middleware_no_origins():
    """Test CORS disabled when no origins specified."""


def test_build_cors_middleware_with_origins():
    """Test CORS enabled with specified origins."""


def test_parse_csv_valid():
    """Test CSV parsing with valid input."""


def test_parse_csv_empty():
    """Test CSV parsing with empty input."""

# ... 6 more tests
```

**test_auth.py** (6 hours, 15 tests)

```python
def test_resolve_auth_class_path_alias():
    """Test alias resolution (github -> full path)."""


def test_resolve_auth_class_path_full():
    """Test full path passthrough."""


def test_import_auth_class_valid():
    """Test successful auth class import."""


def test_import_auth_class_invalid():
    """Test error handling for invalid path."""

# ... 11 more tests
```

**test_static_proxies.py** (5 hours, 18 tests)

```python
def test_namespace_from_path_valid():
    """Test namespace extraction from .mcp.json."""


def test_namespace_from_path_invalid():
    """Test None return for non-.mcp.json files."""


def test_load_config_file_valid():
    """Test JSON config loading."""


def test_load_config_file_invalid_json():
    """Test error handling for invalid JSON."""

# ... 14 more tests
```

**test_server.py** (4 hours, 20 tests)

```python
def test_resolve_server_bind_defaults():
    """Test server bind resolution with defaults."""


def test_resolve_server_bind_custom():
    """Test server bind with custom values."""


def test_health_check_endpoint():
    """Test /health endpoint response."""


def test_health_check_format():
    """Test health response JSON format."""

# ... 16 more tests
```

**Phase 2: Integration Tests (16 hours)**

- Full proxy initialization flow
- Multi-proxy scenarios
- Request routing
- Auth middleware integration
- CORS middleware integration
- Error handling scenarios

**Owner:** QA Team (1-2 people)  
**Timeline:** 2 weeks  
**Target Coverage:** 80%+

---

### ACTION #6: Audit and Document API Endpoints ⏱️ 8 hours

**Issue:** Only `/health` endpoint documented (Section 6 incomplete)

**File to Create:** `API_ENDPOINTS.md`

**Content Outline:**

```markdown
# MCP Proxy Server - API Reference

## Endpoints

### 1. Health Check

- **Path:** GET /health
- **Purpose:** Monitor server health and readiness
- **Response:**
  ```json
  {
    "status": "healthy",
    "service": "drunk-mcp-proxy"
  }
  ```

- **Status Code:** 200 OK
- **Use Cases:**
    - Kubernetes liveness probes
    - Load balancer health checks
    - Monitoring systems

### 2. Tool Access (Dynamic)

- **Path:** POST / (via FastMCP)
- **Method:** POST
- **Body:** MCP protocol message
- **Example Tool Name:**
    - Without namespace: `get_stock_price`
    - With namespace: `stock.get_stock_price`

### 3. [Additional endpoints from FastMCP...]

## Request Format

## Response Format

## Error Responses

## Authentication

## Rate Limiting

## Examples

```

**Also Create:** `openapi.yaml` (OpenAPI 3.0 spec)

**Owner:** Tech Writer + Backend Lead  
**Timeline:** 1 week

---

## MEDIUM-TERM ACTIONS (Complete Weeks 3-4)

### ACTION #7: Implement Token Refresh Logic ⏱️ 20 hours

**Issue:** Auth system doesn't handle token lifecycle (security concern)

**Files to Modify:**
- `src/app/auth.py` - Add token refresh methods
- `src/app/server.py` - Integrate token refresh into request flow

**Implementation Outline:**

```python
# In auth.py, add:

class TokenManager:
    """Manage token lifecycle (expiration, refresh)."""
    
    def __init__(self, provider):
        self.provider = provider
        self.token_cache = {}
        self.expiration_times = {}
    
    def is_token_expired(self, token_id: str) -> bool:
        """Check if token has expired."""
        
    def refresh_token(self, token_id: str) -> str:
        """Refresh expired token and return new token."""
        
    def get_valid_token(self, token_id: str) -> str:
        """Get valid token, refreshing if necessary."""

# In server.py, integrate into request middleware:
def token_validation_middleware():
    """Validate and refresh tokens as needed."""
    async def middleware(request: Request, call_next):
        # Validate token in headers
        # Refresh if needed
        # Add new token to response headers
        response = await call_next(request)
        return response
```

**Owner:** Security Engineer  
**Timeline:** 2 weeks  
**Dependency:** Actions #1-6 complete

---

### ACTION #8: Extend Health Monitoring ⏱️ 6 hours

**Issue:** Health check doesn't aggregate backend status

**File:** `src/app/server.py`

**Current Implementation:**

```python
async def _health_check(request: Request) -> JSONResponse:
    return JSONResponse({
        "status": "healthy",
        "service": SERVER_NAME
    })
```

**Enhanced Implementation:**

```python
async def _health_check(request: Request) -> JSONResponse:
    """Enhanced health check including backend status."""

    backend_status = {}
    for namespace, proxy in get_mounted_proxies():  # Need this function
        try:
            # Try to call a health check on backend
            status = await proxy.health_check()
            backend_status[namespace] = {
                "status": status,
                "healthy": True
            }
        except Exception as e:
            backend_status[namespace] = {
                "status": str(e),
                "healthy": False
            }

    # Aggregate status
    all_healthy = all(
        s.get("healthy", False)
        for s in backend_status.values()
    )

    return JSONResponse({
        "status": "healthy" if all_healthy else "degraded",
        "service": SERVER_NAME,
        "backends": backend_status,
        "timestamp": datetime.now().isoformat()
    })
```

**Owner:** Backend Lead  
**Timeline:** 1 week

---

### ACTION #9: Generate OpenAPI Specification ⏱️ 16 hours

**Approach 1: Manual** (16 hours)

- Write openapi.yaml manually based on code inspection

**Approach 2: Automated** (8 hours)

- Use tool like Starlette's OpenAPI integration
- Or use FastAPI style decorators to auto-generate

**Recommended:** Approach 2 (faster) if FastMCP supports it, else Approach 1

**Output Files:**

- `openapi.yaml` - OpenAPI 3.0 specification
- `API_REFERENCE.md` - Human-readable version
- `examples/` - Example requests/responses

**Owner:** Backend Lead + Tech Writer  
**Timeline:** 1 week

---

## LONG-TERM ACTIONS (Complete Weeks 5-6)

### ACTION #10: Implement Performance Baseline Testing ⏱️ 12 hours

**Deliverables:**

```bash
# tests/performance/test_performance.py
class TestStartupPerformance:
    def test_startup_time_under_5_seconds(self):
        """Startup should complete in <5 seconds."""
        
class TestRequestLatency:
    def test_request_latency_p50_under_100ms(self):
        """p50 latency should be <100ms."""
        
    def test_request_latency_p99_under_500ms(self):
        """p99 latency should be <500ms."""
        
class TestThroughput:
    def test_concurrent_requests_1000_per_second(self):
        """Should handle >1000 concurrent requests/sec."""

class TestMemoryUsage:
    def test_memory_under_200mb_baseline(self):
        """Memory usage should stay under 200MB."""
```

**Owner:** QA Team  
**Timeline:** 1 week

---

### ACTION #11: Implement File-Based Logging ⏱️ 12 hours

**Issue:** Logging is console-only (production needs file logging)

**File:** `src/tools/logging_config.py`

**Enhancement:**

```python
import logging.handlers


def setup_logging(name: str = "mcp-proxy", enable_file: bool = True) -> logging.Logger:
    """
    Configure logging with optional file output.
    
    Args:
        name: Logger name
        enable_file: If True, also log to rotating file
    """
    # ... existing console logging config ...

    logger = logging.getLogger(name)

    if enable_file:
        # Add file handler with rotation
        log_file = os.environ.get("FASTMCP_LOG_FILE", "logs/mcp-proxy.log")
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10_000_000,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s: %(message)s"
        ))
        logger.addHandler(file_handler)

    return logger
```

**Owner:** Backend Lead  
**Timeline:** 1 week

---

## VALIDATION & VERIFICATION

### Pre-Release Checklist

- [ ] All 3 critical issues resolved
- [ ] All 5 high-priority issues resolved
- [ ] Unit test coverage ≥80%
- [ ] Integration tests passing
- [ ] Docker build & run successful
- [ ] Performance baselines measured and acceptable
- [ ] API documentation complete
- [ ] Security audit passed
- [ ] Code review approved
- [ ] Product sign-off obtained

### Testing Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/ -v --cov=src --cov-report=html

# Check code quality
flake8 src/
mypy src/
pylint src/

# Test Docker
docker build -t drunk-mcp-proxy:test .
docker run -p 9123:9123 drunk-mcp-proxy:test

# Test health endpoint
curl http://localhost:9123/health
```

---

## SUCCESS METRICS

| Metric            | Target | Current | Status |
|-------------------|--------|---------|--------|
| Test Coverage     | ≥80%   | 0%      | 🔴     |
| Type Hints        | ≥95%   | 94%     | ✅      |
| Docstrings        | 100%   | 88%     | 🔄     |
| Critical Issues   | 0      | 3       | 🔴     |
| High Issues       | 0      | 5       | 🔴     |
| Code Quality      | A-     | B+      | 🔄     |
| API Documentation | 100%   | 33%     | 🔴     |
| Deployment Ready  | 100%   | 60%     | 🔄     |

---

## TIMELINE SUMMARY

```
THIS WEEK:     4 hours  - Fix critical issues
WEEK 1-2:     60 hours  - Testing foundation & API docs
WEEK 3-4:     40 hours  - Testing execution & performance
WEEK 5-6:     50 hours  - Security & advanced features
─────────────────────────
TOTAL:       154 hours  (~4 weeks @ 40 hrs/week)
```

---

**Document Owner:** Project Lead  
**Last Review:** February 13, 2026  
**Next Review:** Weekly status updates

