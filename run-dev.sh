#!/bin/bash
# Docker Compose development server with live reload

set -e

# Get the project root directory (where this script is located)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "${GREEN}  drunk-mcp-proxy Docker Compose${NC}"
echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "${BLUE}Project Root:${NC} $PROJECT_ROOT"
echo ""

# Create data directory
mkdir -p "$PROJECT_ROOT/data"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "${RED}✗ Docker daemon is not running${NC}"
    exit 1
fi

echo "${GREEN}✓ Docker is running${NC}"
echo ""

# Check if docker-compose exists
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "${RED}✗ Docker Compose is not installed${NC}"
    exit 1
fi

echo "${GREEN}✓ Docker Compose is available${NC}"
echo ""

export DOCKER_BUILDKIT=1
# Get the action (default to up)
ACTION=${1:-up}
PORT=${2:-8000}

case "$ACTION" in
    up|start)
        echo "${BLUE}Building and starting Docker Compose...${NC}"

        # Build the image
        echo "${BLUE}Building Docker image...${NC}"
        docker-compose build

        echo ""
        echo "${GREEN}✓ Build complete${NC}"
        echo ""

        # Start the container
        echo "${BLUE}Starting container...${NC}"
        echo "  Service: ${YELLOW}mcp-proxy${NC}"
        echo "  Image: ${YELLOW}drunk-mcp-proxy:latest${NC}"
        echo "  Port: ${YELLOW}${PORT}:8000${NC}"
        echo "  Data: ${YELLOW}${PROJECT_ROOT}/data:/app/data${NC}"
        echo ""

        docker-compose up -d

        echo ""
        echo "${GREEN}✓ Container started${NC}"
        echo ""
        echo "${BLUE}Service Information:${NC}"
        docker-compose ps
        echo ""
        echo "${GREEN}✓ Services running:${NC}"
        echo "  MCP Proxy:     http://localhost:8000"
        echo "  MCP Inspector: http://127.0.0.1:6274"
        echo ""
        ;;

    down|stop)
        echo "${BLUE}Stopping Docker Compose...${NC}"
        docker-compose down
        echo "${GREEN}✓ Container stopped${NC}"
        ;;

    logs)
        echo "${BLUE}Showing Docker Compose logs...${NC}"
        docker-compose logs -f
        ;;

    restart)
        echo "${BLUE}Restarting Docker Compose...${NC}"
        docker-compose restart
        echo "${GREEN}✓ Container restarted${NC}"
        ;;

    status|ps)
        echo "${BLUE}Docker Compose Status:${NC}"
        docker-compose ps
        ;;

    *)
        echo "${YELLOW}Usage:${NC}"
        echo "  bash docker-dev.sh [COMMAND] [PORT]"
        echo ""
        echo "${YELLOW}Commands:${NC}"
        echo "  up       - Build and start container (default)"
        echo "  down     - Stop and remove container"
        echo "  stop     - Alias for down"
        echo "  logs     - View container logs"
        echo "  restart  - Restart container"
        echo "  status   - Show container status"
        echo "  ps       - Alias for status"
        echo ""
        echo "${YELLOW}Examples:${NC}"
        echo "  bash docker-dev.sh up"
        echo "  bash docker-dev.sh down"
        echo "  bash docker-dev.sh logs"
        echo "  bash docker-dev.sh restart"
        exit 1
        ;;
esac

echo ""
