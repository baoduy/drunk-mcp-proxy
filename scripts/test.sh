#!/bin/bash
# Run comprehensive tests

set -e

# Get the project root directory (parent of scripts folder)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root so relative paths work
cd "$PROJECT_ROOT"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "${GREEN}  drunk-mcp-proxy Test Suite${NC}"
echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "${BLUE}Project Root:${NC} $PROJECT_ROOT"
echo ""

TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to run a test
run_test() {
    local test_name=$1
    local test_cmd=$2

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    echo "${BLUE}Test ${TOTAL_TESTS}: ${test_name}${NC}"

    if eval "$test_cmd" > /tmp/test_output.log 2>&1; then
        echo "${GREEN}✓ PASSED${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo "${RED}✗ FAILED${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        cat /tmp/test_output.log
    fi
    echo ""
}

# Test 1: Python syntax check
run_test "Python syntax check" \
    "python3 -m py_compile src/main.py"

# Test 2: Validate JSON config files
run_test "Validate mcp.example.json" \
    "python3 -m json.tool mcp.example.json > /dev/null"

# Test 3: Create data directory and copy config
mkdir -p data
if [ ! -f data/mcp.json ]; then
    cp mcp.example.json data/mcp.json
fi

run_test "Validate data/mcp.json" \
    "python3 -m json.tool data/mcp.json > /dev/null"

# Test 4: Validate schema files
run_test "Validate mcp.schema.json" \
    "python3 -m json.tool schemas/mcp.schema.json > /dev/null"

run_test "Validate auth.schema.json" \
    "python3 -m json.tool schemas/auth.schema.json > /dev/null"

run_test "Validate proxies.schema.json" \
    "python3 -m json.tool schemas/proxies.schema.json > /dev/null"

# Test 5: Check Python imports
run_test "Check Python imports" \
    'python3 -c "import sys; sys.path.insert(0, \"src\"); import validation, auth, main"'

# Test 6: Check if requirements are installed (if venv exists)
if [ -d "venv" ]; then
    run_test "Check if fastmcp is installed" \
        "python3 -c \"import fastmcp\""

    run_test "Check if jsonschema is installed" \
        "python3 -c \"import jsonschema\""
fi

# Print summary
echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "${GREEN}Test Summary${NC}"
echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "Total:  ${YELLOW}${TOTAL_TESTS}${NC}"
echo "Passed: ${GREEN}${PASSED_TESTS}${NC}"
echo "Failed: ${RED}${FAILED_TESTS}${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo "${RED}✗ Some tests failed!${NC}"
    exit 1
fi
