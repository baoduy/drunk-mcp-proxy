#!/bin/bash
# Code quality and linting script

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
echo "${GREEN}  drunk-mcp-proxy Code Quality Check${NC}"
echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "${BLUE}Project Root:${NC} $PROJECT_ROOT"
echo ""

ISSUES_FOUND=0

# Check Python syntax
echo "${BLUE}Checking Python syntax...${NC}"
for file in "$PROJECT_ROOT"/src/*.py; do
    if python3 -m py_compile "$file" 2>/dev/null; then
        echo "${GREEN}✓ $(basename $file)${NC}"
    else
        echo "${RED}✗ $(basename $file) has syntax errors${NC}"
        python3 -m py_compile "$file"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    fi
done
echo ""

# Check for common Python issues (if pylint is installed)
if command -v pylint &> /dev/null; then
    echo "${BLUE}Running pylint...${NC}"

    for file in "$PROJECT_ROOT"/src/*.py; do
        if pylint "$file" --disable=all --enable=syntax-error 2>/dev/null; then
            echo "${GREEN}✓ $(basename $file)${NC}"
        else
            echo "${YELLOW}⚠️  $file has warnings${NC}"
        fi
    done
    echo ""
else
    echo "${YELLOW}⚠️  pylint not installed (install with: pip install pylint)${NC}"
    echo ""
fi

# Check for unused imports (if vulture is installed)
if command -v vulture &> /dev/null; then
    echo "${BLUE}Checking for dead code...${NC}"
    vulture "$PROJECT_ROOT/src/" --min-confidence 100 || true
    echo ""
else
    echo "${YELLOW}⚠️  vulture not installed (install with: pip install vulture)${NC}"
    echo ""
fi

# Validate JSON files
echo "${BLUE}Validating JSON files...${NC}"

for file in "$PROJECT_ROOT"/mcp.example.json "$PROJECT_ROOT"/schemas/*.json; do
    if [ -f "$file" ]; then
        if python3 -m json.tool "$file" > /dev/null 2>&1; then
            echo "${GREEN}✓ $(basename $file)${NC}"
        else
            echo "${RED}✗ $(basename $file) is invalid JSON${NC}"
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
        fi
    fi
done

if [ -f "$PROJECT_ROOT/data/mcp.json" ]; then
    if python3 -m json.tool "$PROJECT_ROOT/data/mcp.json" > /dev/null 2>&1; then
        echo "${GREEN}✓ data/mcp.json${NC}"
    else
        echo "${RED}✗ data/mcp.json is invalid JSON${NC}"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    fi
fi

echo ""

# Summary
if [ $ISSUES_FOUND -eq 0 ]; then
    echo "${GREEN}✓ No issues found!${NC}"
    exit 0
else
    echo "${RED}✗ Found ${ISSUES_FOUND} issue(s)${NC}"
    exit 1
fi

