#!/bin/bash
# Clean up development environment

# Get the project root directory (parent of scripts folder)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "${GREEN}  drunk-mcp-proxy Clean Script${NC}"
echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "${BLUE}Project Root:${NC} $PROJECT_ROOT"
echo ""

# Confirm before deleting
read -p "${YELLOW}This will remove virtual environment, cache, and Docker images. Continue? (y/n) ${NC}" -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 1
fi

echo ""

# Remove virtual environment
if [ -d "$PROJECT_ROOT/venv" ]; then
    echo "${BLUE}Removing virtual environment...${NC}"
    rm -rf "$PROJECT_ROOT/venv"
    echo "${GREEN}✓ Virtual environment removed${NC}"
fi

# Remove Python cache
echo "${BLUE}Removing Python cache...${NC}"
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
echo "${GREEN}✓ Python cache cleaned${NC}"

# Remove Docker images and containers
if command -v docker &> /dev/null; then
    echo "${BLUE}Cleaning Docker...${NC}"

    # Stop and remove dev container
    if docker ps -a --format '{{.Names}}' | grep -q "^mcp-proxy-dev$"; then
        docker stop mcp-proxy-dev 2>/dev/null || true
        docker rm mcp-proxy-dev 2>/dev/null || true
        echo "${GREEN}✓ Development container removed${NC}"
    fi

    # Stop and remove production container
    if docker ps -a --format '{{.Names}}' | grep -q "^mcp-proxy-server$"; then
        docker-compose down 2>/dev/null || true
        echo "${GREEN}✓ Production container removed${NC}"
    fi

    # Remove images
    if docker images --format '{{.Repository}}:{{.Tag}}' | grep -q "^drunk-mcp-proxy:"; then
        docker rmi drunk-mcp-proxy:dev 2>/dev/null || true
        docker rmi drunk-mcp-proxy:latest 2>/dev/null || true
        docker rmi drunk-mcp-proxy:test 2>/dev/null || true
        echo "${GREEN}✓ Docker images removed${NC}"
    fi
fi

# Clean temporary files
echo "${BLUE}Removing temporary files...${NC}"
rm -f /tmp/test_output.log /tmp/docker-build.log
echo "${GREEN}✓ Temporary files cleaned${NC}"

echo ""
echo "${GREEN}✓ Cleanup complete!${NC}"
echo ""
echo "To set up again, run:"
echo "  ${BLUE}bash scripts/setup-env.sh${NC}"
echo ""

