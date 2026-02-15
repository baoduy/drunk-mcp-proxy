#!/bin/bash

# Script to run all unit tests for drunk-mcp-proxy
# Usage: ./scripts/run-tests.sh [pytest options]

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Get the project root directory (parent of scripts)
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

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
    .venv/bin/pip install pytest
fi

echo "🧪 Running all tests..."
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

# Run pytest with all tests in the tests directory
# Pass any additional arguments to pytest (e.g., -v, -k, --tb=short)
# Default to verbose output
if [ $# -eq 0 ]; then
    .venv/bin/python -m pytest tests/ -v
else
    .venv/bin/python -m pytest tests/ "$@"
fi

# Capture the exit code
TEST_EXIT_CODE=$?

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ All tests passed! ($TEST_FILES test file(s) executed successfully)"
else
    echo "❌ Some tests failed (exit code: $TEST_EXIT_CODE)"
    echo "💡 Run with -v for verbose output: ./scripts/tests.sh -v"
    echo "💡 Run specific test: ./scripts/tests.sh -k test_name"
fi

exit $TEST_EXIT_CODE
