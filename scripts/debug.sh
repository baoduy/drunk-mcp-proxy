#!/bin/bash
# Debug script with verbose logging and pdb debugging support

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
echo "${GREEN}  drunk-mcp-proxy Debug Mode${NC}"
echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "${BLUE}Project Root:${NC} $PROJECT_ROOT"
echo ""

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "${YELLOW}⚠️  Virtual environment not activated${NC}"
    echo "Activating venv..."
    source "$PROJECT_ROOT/venv/bin/activate"
fi

# Create data directory
mkdir -p "$PROJECT_ROOT/data"

# Check configuration files
echo "${GREEN}Checking configuration files:${NC}"

if [ ! -f "$PROJECT_ROOT/data/mcp.json" ]; then
    echo "${RED}✗ data/mcp.json not found${NC}"
    if [ -f "$PROJECT_ROOT/mcp.example.json" ]; then
        cp "$PROJECT_ROOT/mcp.example.json" "$PROJECT_ROOT/data/mcp.json"
        echo "${GREEN}✓ Copied mcp.example.json to data/mcp.json${NC}"
    else
        echo "${RED}✗ mcp.example.json not found either${NC}"
        exit 1
    fi
else
    echo "${GREEN}✓ data/mcp.json found${NC}"
fi

# Validate JSON
echo ""
echo "${GREEN}Validating configuration files:${NC}"

if python3 -m json.tool "$PROJECT_ROOT/data/mcp.json" > /dev/null 2>&1; then
    echo "${GREEN}✓ data/mcp.json is valid JSON${NC}"
else
    echo "${RED}✗ data/mcp.json is INVALID JSON${NC}"
    python3 -m json.tool "$PROJECT_ROOT/data/mcp.json"
    exit 1
fi

# Check Python syntax
echo ""
echo "${GREEN}Checking Python files syntax:${NC}"

for file in src/main.py; do
    if [ -f "$file" ]; then
        if python3 -m py_compile "$file" 2>/dev/null; then
            echo "${GREEN}✓ $file${NC}"
        else
            echo "${RED}✗ $file has syntax errors:${NC}"
            python3 -m py_compile "$file"
            exit 1
        fi
    fi
done

# Check imports
echo ""
echo "${GREEN}Checking imports:${NC}"

python3 << 'EOF'
import sys
sys.path.insert(0, 'src')

try:
    import validation
    print("\033[0;32m✓ validation module imports correctly\033[0m")
except Exception as e:
    print(f"\033[0;31m✗ validation module import failed: {e}\033[0m")
    sys.exit(1)

try:
    import auth
    print("\033[0;32m✓ auth module imports correctly\033[0m")
except Exception as e:
    print(f"\033[0;31m✗ auth module import failed: {e}\033[0m")
    sys.exit(1)

try:
    import main
    print("\033[0;32m✓ main module imports correctly\033[0m")
except Exception as e:
    print(f"\033[0;31m✗ main module import failed: {e}\033[0m")
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    exit 1
fi

# Set environment variables for debugging
echo ""
echo "${GREEN}Setting debug environment variables:${NC}"
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1
export FASTMCP_CONFIG_DIR="data"
export PYTHONPATH="src"
export DEBUG=1

echo "  PYTHONUNBUFFERED=1"
echo "  PYTHONDONTWRITEBYTECODE=1"
echo "  FASTMCP_CONFIG_DIR=data"
echo "  PYTHONPATH=src"
echo "  DEBUG=1"
echo ""

# Display usage
echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "${GREEN}Debug Mode Ready${NC}"
echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Run with one of these options:"
echo ""
echo "${YELLOW}1. Run with verbose output:${NC}"
echo "   python3 -v src/main.py"
echo ""
echo "${YELLOW}2. Run with debugger (pdb):${NC}"
echo "   python3 -m pdb src/main.py"
echo ""
echo "${YELLOW}3. Run with profiling:${NC}"
echo "   python3 -m cProfile -s cumulative src/main.py"
echo ""
echo "${YELLOW}4. Run normally (with debug env vars):${NC}"
echo "   python3 src/main.py"
echo ""
echo "${YELLOW}5. Interactive Python shell (for testing):${NC}"
echo "   python3 -i src/main.py"
echo ""
echo "To exit debug mode, press Ctrl+C or type: ${BLUE}exit()${NC}"
echo ""

# Start interactive Python shell
python3 -i src/main.py
