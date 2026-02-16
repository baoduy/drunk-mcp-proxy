# Code Coverage Setup - drunk-mcp-proxy

## Overview

Code coverage has been successfully configured and applied to the **drunk-mcp-proxy** project. This setup provides
comprehensive testing metrics and multiple report formats to track code quality and test completeness.

## What's Been Installed

### Coverage Tools

- **coverage** (v7.13.4): Core code coverage measurement tool
- **pytest-cov** (v7.0.0): pytest plugin for coverage integration

### Coverage Configuration Files Created

1. **`.coveragerc`** - Main coverage configuration file
    - Location: Project root directory
    - Purpose: Controls coverage measurement behavior
    - Key settings:
        - Source packages: `src/`
        - Branch coverage: Enabled
        - Parallel testing: Enabled
        - Excludes: test files, __pycache__, site-packages, .venv

## Current Coverage Metrics

As of the latest test run:

```
Overall Coverage: 78.19%
├── Covered Lines:    494
├── Total Statements: 638
├── Missing Lines:    144
└── Excluded Lines:   12
```

### Coverage by Module

| Module                                | Coverage | Status      |
|---------------------------------------|----------|-------------|
| src/tools/azure_oauth.py              | 100%     | ✓ Excellent |
| src/tools/env_resolver.py             | 100%     | ✓ Excellent |
| src/tools/logging_config.py           | 100%     | ✓ Excellent |
| src/proxies/config_provider.py        | 96.94%   | ✓ Excellent |
| src/tools/spec_config.py              | 94.66%   | ✓ Excellent |
| src/tools/env.py                      | 92.00%   | ✓ Good      |
| src/proxies/openapi_mcp_provider.py   | 79.01%   | ⚠ Fair      |
| src/tools/cache.py                    | 79.55%   | ⚠ Fair      |
| src/main.py                           | 81.82%   | ✓ Good      |
| src/app/middleware/cros_middleware.py | 100%     | ✓ Excellent |
| src/app/middleware/__init__.py        | 100%     | ✓ Excellent |
| src/app/__init__.py                   | 100%     | ✓ Excellent |
| src/proxies/mcp_proxy_config.py       | 100%     | ✓ Excellent |
| src/app/starlette_app.py              | 32.69%   | ✗ Low       |
| src/app/server.py                     | 27.42%   | ✗ Low       |
| src/app/lifespan.py                   | 20.69%   | ✗ Very Low  |

## Report Formats Generated

### 1. Terminal Report

Shows a summary table of coverage metrics directly in the terminal output.

### 2. JSON Report (`coverage.json`)

- **Location**: Project root
- **Format**: JSON with detailed per-file metrics
- **Purpose**: Machine-readable format for CI/CD integration
- **Contains**: Line execution details, function-level coverage, branch coverage data

### 3. HTML Report (`htmlcov/`)

- **Location**: `htmlcov/index.html` in project root
- **Format**: Interactive HTML with visual highlighting
- **Features**:
    - Overview dashboard with coverage statistics
    - Per-file coverage breakdown with line-by-line highlighting
    - Missing lines highlighted in red
    - Covered lines highlighted in green
    - Interactive navigation and drill-down

## Using the Coverage Tools

### Running Tests with Coverage

#### Run all tests with coverage reports

```bash
./scripts/tests.sh
```

#### Run tests and generate HTML report

```bash
./scripts/tests.sh --html
```

#### Run tests with additional pytest options

```bash
./scripts/tests.sh -v                    # Verbose output
./scripts/tests.sh -k test_name          # Run specific test
./scripts/tests.sh --tb=short            # Custom traceback format
```

#### View the interactive HTML report

```bash
open htmlcov/index.html    # macOS
firefox htmlcov/index.html # Linux
explorer htmlcov\index.html # Windows
```

### Using Coverage Directly

```bash
# Run coverage on specific files/directories
coverage run -m pytest tests/

# Generate reports
coverage report                # Terminal report
coverage html                  # Generate HTML report
coverage json                  # Generate JSON report
coverage xml                   # Generate XML report (for CI)

# View missing lines
coverage report --skip-covered  # Show only files with missing coverage
```

## Test Results Summary

### Test Statistics

- **Total Tests**: 194
- **Passed**: 175
- **Failed**: 18
- **Skipped**: 1
- **Success Rate**: 90.2%

### Known Issues

Some tests are failing due to missing or modified attributes in modules:

- `test_auth.py`: References non-existent `src/app/auth.py` module
- `test_filters.py`: Attempts to access non-existent `name` attribute on SpecConfig
- Various spec_config tests: Schema validation issues

These failures should be investigated and resolved to improve overall coverage.

## Files Modified/Created

### New Files

1. `.coveragerc` - Coverage configuration
2. Updated `scripts/tests.sh` - Enhanced test runner with coverage integration

### Configuration Changes

- Added `--cov=src` to pytest commands to measure only source code
- Added `--cov-report=json` for JSON output
- Added `--cov-report=html` for HTML report generation
- Added `--cov-report=term` for terminal output

## Accessing Coverage Data

### For Continuous Integration

Use the `coverage.json` file in your CI/CD pipeline:

```bash
# Parse JSON in your CI script
python -c "import json; data = json.load(open('coverage.json')); print(data['totals']['percent_covered'])"
```

### For Local Development

1. **Quick View**: Check terminal output after running tests
2. **Detailed View**: Open `htmlcov/index.html` in your browser
3. **Programmatic Access**: Parse `coverage.json` for metrics

## Improving Coverage

### Low Coverage Areas

- **src/app/lifespan.py**: 20.69% - Create integration tests for AppLifespanManager
- **src/app/server.py**: 27.42% - Add tests for MCPProxyServer initialization and methods
- **src/app/starlette_app.py**: 32.69% - Add tests for StarletteApp configuration and routing

### Recommendations

1. Add tests for uncovered modules in `src/app/`
2. Test edge cases and error conditions
3. Add integration tests for server startup and configuration
4. Fix failing tests to increase success rate

## Best Practices

1. **Run coverage locally before committing**
   ```bash
   ./scripts/tests.sh --html
   ```

2. **Check HTML report for visual coverage**
    - Open `htmlcov/index.html` to see which lines are untested
    - Click on files to see detailed line-by-line coverage

3. **Set coverage thresholds**
    - Consider requiring minimum 80% coverage for new code
    - Add `--cov-fail-under=80` to fail tests if coverage drops

4. **Keep coverage configuration updated**
    - Update `.coveragerc` as new modules are added
    - Review excluded patterns regularly

## Additional Resources

- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [HTML Coverage Report](htmlcov/index.html) - View local report

## Quick Reference Commands

```bash
# View coverage in terminal
./scripts/tests.sh

# Generate and open HTML report
./scripts/tests.sh --html && open htmlcov/index.html

# Run specific test with coverage
./scripts/tests.sh -k test_name --html

# Combine with other pytest options
./scripts/tests.sh -v --tb=short --html

# Check coverage percentage
grep "TOTAL" <(./scripts/tests.sh)
```

---

**Last Updated**: February 16, 2026
**Coverage Tool Version**: coverage 7.13.4
**pytest-cov Version**: 7.0.0

