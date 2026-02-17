# Project Memory: drunk-mcp-proxy

## 📋 Project Structure Rules

### Markdown File Organization (IMPORTANT)

✅ **ALL NEW markdown files (.md) that you GENERATE must be placed in appropriate subdirectories under `./docs/`**

**Do NOT create new markdown files in the project root!**

*Note: Existing root files like README.md, QUICK_START.md can remain. This rule applies to NEW documents you create
during development.*

### Test and Verification Files Organization (IMPORTANT)

✅ **ALL unit tests and verification Python files (.py) must be placed in `./tests/` folder**

**Do NOT create test files in the project root or other directories!**

Examples of files that go in `./tests/`:

- `test_*.py` - Unit test files
- `*_test.py` - Alternative test format
- `verify_*.py` - Verification scripts
- `conftest.py` - Pytest configuration

### Documentation Directory Structure

```
docs/
├── analysis/          # Analysis reports, test coverage, verification reports
├── architecture/      # Architecture diagrams, specifications, design docs
├── development/       # Development guides, implementation checklists, quick refs
├── features/          # Feature documentation, implementation details
├── guides/            # User guides, how-to documents
├── planning/          # Project planning, task breakdowns, checklists
├── refactoring/       # Refactoring documentation, improvement plans
└── README.md          # Main documentation index
```

### Where to Place Each Type of Document

| Document Type            | Directory            | Examples                                                    |
|--------------------------|----------------------|-------------------------------------------------------------|
| Test Reports             | `docs/analysis/`     | TEST_COVERAGE_SUMMARY.md, OAUTH_CLIENT_TEST_REPORT.md       |
| Bug Fixes                | `docs/analysis/`     | REMEDIATION_PLAN.md, FINAL_VERIFICATION_REPORT.md           |
| Implementation Summaries | `docs/analysis/`     | COMPLETION_SUMMARY.md, FINAL_IMPLEMENTATION_SUMMARY.md      |
| Architecture Docs        | `docs/architecture/` | ARCHITECTURE_DIAGRAMS.md, SPECIFICATION.md                  |
| Development Guides       | `docs/development/`  | BUILD_MCP_SERVERS_QUICK_REF.md, IMPLEMENTATION_CHECKLIST.md |
| Feature Documentation    | `docs/features/`     | Feature guides, API documentation                           |
| User Guides              | `docs/guides/`       | How-to guides, setup guides                                 |
| Planning Documents       | `docs/planning/`     | TASK_BREAKDOWN.md, TASK_CHECKLIST.md                        |
| Refactoring Docs         | `docs/refactoring/`  | Refactoring summaries, improvement plans                    |

## 🔐 Project Status

### Completed Tasks ✅

1. **Fixed OAuth Client Errors** (Feb 15, 2026)
    - ✅ Fixed: `AttributeError: 'OauthAsyncClient' object has no attribute 'base_url'`
    - ✅ Fixed: `AttributeError: 'OauthAsyncClient' object has no attribute 'headers'`
    - ✅ Fixed: `AttributeError: 'OauthAsyncClient' object has no attribute 'send'`
    - Implementation: `src/tools/oauth_client.py`

2. **Added Comprehensive Test Coverage** (Feb 15, 2026)
    - ✅ Created: `tests/test_oauth_async_client.py` (22 tests)
    - ✅ Fixed: `tests/test_openapi_oauth_client.py` (2 tests)
    - ✅ Result: 55/55 tests passing (100% success rate)

3. **Test Reports Generated**
    - `docs/analysis/TEST_COVERAGE_SUMMARY.md`
    - `docs/analysis/OAUTH_CLIENT_TEST_REPORT.md`

## 🛠 Key Implementation Details

### OauthAsyncClient Enhancements

**Properties Added (5 total):**

```python
@property
def base_url(self): ...  # Base URL from httpx.AsyncClient


@property
def headers(self): ...  # Headers from httpx.AsyncClient


@property
def timeout(self): ...  # Timeout configuration


@property
def is_closed(self) -> bool: ...  # Connection status


@property
def params(self): ...  # Query parameters
```

**Methods Added (2 total):**

```python
async def send(self, request: httpx.Request, **kwargs) -> httpx.Response:
    """Send prepared request with OAuth token injection"""


def build_request(self, method: str, url: str, **kwargs) -> httpx.Request:
    """Build HTTP request without sending"""
```

## 🧪 Testing Standards

### Test Organization

- All tests in `tests/` directory
- Use pytest framework
- Run with: `python -m pytest tests/ -v`

### Test File Naming

- Use `test_<module_name>.py` format
- Example: `test_oauth_async_client.py`

### Test Class Organization

- Group related tests in classes
- Use descriptive class names
- Each class focuses on one aspect

## 📦 Important Files

### Configuration

- `requirements.txt` - Project dependencies (includes pytest, pytest-asyncio)
- `pytest.ini` - Pytest configuration
- `pyproject.toml` - Project metadata (if exists)

### Documentation

- `docs/` - Main documentation folder
- `README.md` - Project overview
- All new documentation must go in subdirectories under `docs/`

### Source Code

- `src/tools/oauth_client.py` - OAuth client implementation
- `src/proxies/openapi_mcp_provider.py` - OpenAPI proxy provider
- `src/app/server.py` - Main server

### Tests (ALL IN `./tests/` FOLDER)

✅ **IMPORTANT: ALL test and verification files must be in `./tests/` folder**

- `tests/test_oauth_async_client.py` - OAuth client tests (22 tests)
- `tests/test_openapi_oauth_client.py` - OAuth provider tests (2 tests)
- `tests/test_spec_config.py` - Configuration tests (28 tests)
- `tests/test_env_resolution.py` - Environment tests (3 tests)
- `tests/verify_*.py` - Verification scripts
- `tests/conftest.py` - Pytest configuration fixtures

## 🚀 Development Workflow

### When Adding New Features

1. Implement feature in appropriate source file
2. Create tests in `tests/` directory
3. Ensure all tests pass: `python -m pytest tests/ -v`
4. Generate documentation in appropriate `docs/` subdirectory
5. Update this memory if structure changes

### When Fixing Bugs

1. Reproduce bug with failing test
2. Fix code in source file
3. Verify test now passes
4. Add documentation to `docs/analysis/` if significant

### When Documenting

1. **ALWAYS** place markdown files in `docs/` subdirectories
2. **NEVER** create .md files in project root
3. Use appropriate subdirectory based on content type

### When Creating Tests or Verification Scripts

1. **ALWAYS** place test files in `tests/` directory
2. Use `test_*.py` or `verify_*.py` naming convention
3. **NEVER** create test files in project root
4. Run all tests before committing: `python -m pytest tests/ -v`

## 📊 Test Coverage

### Current Status (Feb 15, 2026)

- **Total Tests:** 55
- **Passing:** 55 ✅
- **Failing:** 0 ✅
- **Success Rate:** 100%
- **Execution Time:** ~0.25 seconds

### Test Breakdown

- OauthAsyncClient Tests: 22 ✅
- OAuth Provider Tests: 2 ✅
- Spec Config Tests: 28 ✅
- Environment Resolution Tests: 3 ✅

## 🔄 Project Technologies

### Core Dependencies

- **FastMCP** - MCP server framework
- **httpx** - HTTP client library
- **pydantic** - Data validation
- **pytest** - Testing framework
- **starlette** - Web framework

### Features

- OAuth 2.0 Client Credentials flow
- Azure Entra ID authentication
- OpenAPI integration
- MCP protocol support
- Environment variable resolution

## ⚠️ Important Notes

1. **Documentation Location**: Always put markdown files in `docs/` subdirectories (NEVER in root)
2. **Test Location**: Always put test/verification files in `tests/` directory (NEVER in root)
3. **Test Standards**: All code changes require corresponding tests
4. **Code Quality**: Maintain 100% test pass rate
5. **Version Control**: Keep memory updated with new conventions

## 🎯 Future Tasks

When you work on new tasks:

1. Remember to place ALL .md files in appropriate `docs/` subdirectories
2. Remember to place ALL test/verification .py files in `tests/` directory
3. Update test files to maintain 100% pass rate
4. Follow existing code structure and patterns
5. Document all changes with appropriate test coverage
6. Update this memory if you discover new project conventions

---

**Last Updated:** February 15, 2026
**Project Status:** Production Ready ✅
**Test Coverage:** 100% (55/55 tests passing)

