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

# Run pytest with all tests in the tests directory
# Pass any additional arguments to pytest (e.g., -v, -k, --tb=short)
.venv/bin/python -m pytest tests/ "$@"

# Capture the exit code
TEST_EXIT_CODE=$?

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ All tests passed!"
else
    echo "❌ Some tests failed (exit code: $TEST_EXIT_CODE)"
fi

exit $TEST_EXIT_CODE
