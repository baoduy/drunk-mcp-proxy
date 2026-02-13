#!/bin/bash
# Development server with automatic reload and debugging

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
NC='\033[0m'

echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "${GREEN}  drunk-mcp-proxy Development Server${NC}"
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

# Check if config exists
if [ ! -f "$PROJECT_ROOT/data/mcp.json" ]; then
    echo "${YELLOW}⚠️  data/mcp.json not found${NC}"
    if [ -f "$PROJECT_ROOT/mcp.example.json" ]; then
        cp "$PROJECT_ROOT/mcp.example.json" "$PROJECT_ROOT/data/mcp.json"
        echo "${GREEN}✓ Copied mcp.example.json to data/mcp.json${NC}"
    fi
fi

# Set environment variables
export PYTHONUNBUFFERED=1
export FASTMCP_CONFIG_FILE="data"
export PYTHONPATH="src"

echo "${GREEN}Configuration:${NC}"
echo "  FASTMCP_CONFIG_FILE: $FASTMCP_CONFIG_FILE"
echo "  PYTHONPATH: $PYTHONPATH"
echo ""

# Check if watchdog is installed for auto-reload
if python3 -c "import watchdog" 2>/dev/null; then
    echo "${GREEN}✓ Using watchdog for auto-reload${NC}"
    echo ""
    echo "${YELLOW}Starting development server with auto-reload...${NC}"
    echo "(Press Ctrl+C to stop)"
    echo ""

    watchmedo auto-restart -d src -p '*.py' -- python3 src/main.py
else
    echo "${YELLOW}⚠️  watchdog not installed - running without auto-reload${NC}"
    echo "Install with: pip install watchdog"
    echo ""
    echo "${YELLOW}Starting development server...${NC}"
    echo "(Press Ctrl+C to stop)"
    echo ""

    python3 src/main.py
fi
