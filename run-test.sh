#!/bin/bash

# Script to run all unit tests with code coverage for drunk-mcp-proxy
# Usage: ./test.sh [pytest options]
# Examples:
#   ./test.sh              # Run all tests with coverage
#   ./test.sh -v           # Run with verbose output
#   ./test.sh --cov        # Show coverage report in terminal
#   ./test.sh --html       # Generate HTML coverage report
#   ./test.sh -k test_auth # Run specific test

set -e

# Get the project root directory (where this script is located)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Check if virtual environment exists
if [ ! -f ".venv/bin/python" ]; then
    echo "❌ Virtual environment not found at .venv/"
    echo "Please create a virtual environment first:"
    echo "  python3 -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Check if pytest is installed
if ! .venv/bin/python -c "import pytest" 2>/dev/null; then
    echo "❌ pytest not found in virtual environment"
    echo "Installing pytest..."
    .venv/bin/pip install pytest pytest-cov
fi

# Check if coverage is installed
if ! .venv/bin/python -c "import coverage" 2>/dev/null; then
    echo "❌ coverage not found in virtual environment"
    echo "Installing coverage..."
    .venv/bin/pip install coverage pytest-cov
fi

echo "🧪 Running tests with code coverage..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if tests directory exists
if [ ! -d "tests" ]; then
    echo "❌ Tests directory not found at ./tests"
    exit 1
fi

# Count test files
TEST_FILES=$(find tests -name "test_*.py" -type f | wc -l)
if [ "$TEST_FILES" -eq 0 ]; then
    echo "⚠️  No test files found in ./tests directory (looking for test_*.py)"
    exit 1
fi

echo "📋 Found $TEST_FILES test file(s):"
find tests -name "test_*.py" -type f | sed 's/^/   ✓ /'
echo ""

# Parse command line arguments
COVERAGE_HTML=false
COVERAGE_REPORT=false

# Check for special flags
for arg in "$@"; do
    if [ "$arg" = "--html" ]; then
        COVERAGE_HTML=true
        # Remove --html from arguments
        set -- "${@/$arg}"
    elif [ "$arg" = "--cov" ]; then
        COVERAGE_REPORT=true
        # Remove --cov from arguments
        set -- "${@/$arg}"
    fi
done

# Build pytest command with coverage
PYTEST_CMD=".venv/bin/python -m pytest tests/ --cov=src --cov-report=json --cov-report=term"

# Add HTML report if requested
if [ "$COVERAGE_HTML" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov-report=html"
fi

# Add additional pytest arguments if provided
if [ $# -gt 0 ]; then
    PYTEST_CMD="$PYTEST_CMD $@"
else
    # Default to verbose output
    PYTEST_CMD="$PYTEST_CMD -v"
fi

echo "📊 Running: $PYTEST_CMD"
echo ""

# Run pytest with coverage
$PYTEST_CMD

# Capture the exit code
TEST_EXIT_CODE=$?

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ All tests passed! ($TEST_FILES test file(s) executed successfully)"
    echo ""
    echo "📊 Coverage Report Location:"
    echo "   • Terminal: See output above"
    echo "   • JSON: ./coverage.json"

    if [ "$COVERAGE_HTML" = true ]; then
        echo "   • HTML: ./htmlcov/index.html"
        echo ""
        echo "💡 Open HTML coverage report in your browser:"
        if command -v open &> /dev/null; then
            echo "   open htmlcov/index.html"
        else
            echo "   firefox htmlcov/index.html  # or your preferred browser"
        fi
    fi

    echo ""
    echo "💡 View summary: coverage report"
    echo "💡 Generate HTML report: ./test.sh --html"
else
    echo "❌ Some tests failed (exit code: $TEST_EXIT_CODE)"
    echo "💡 Run with -v for verbose output: ./test.sh -v"
    echo "💡 Run specific test: ./test.sh -k test_name"
    echo "💡 Generate coverage report: ./test.sh --cov"
    echo "💡 Generate HTML coverage: ./test.sh --html"
fi

exit $TEST_EXIT_CODE
