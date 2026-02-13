#!/bin/bash
# Quick reference helper for all scripts

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Function to print section header
print_header() {
    echo ""
    echo "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo "${GREEN}$1${NC}"
    echo "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Function to print command
print_cmd() {
    echo "${BLUE}$1${NC}"
}

# Show help
if [[ "$1" == "-h" || "$1" == "--help" || -z "$1" ]]; then
    print_header "drunk-mcp-proxy Development Scripts"

    echo ""
    echo "${YELLOW}Usage:${NC} bash scripts/help.sh [COMMAND]"
    echo ""
    echo "${YELLOW}Available commands:${NC}"
    echo ""

    echo "${GREEN}Development${NC}"
    print_cmd "  dev                Run development server"
    print_cmd "  dev-docker         Run development server in Docker"
    print_cmd "  debug              Run with debug mode"
    echo ""

    echo "${GREEN}Testing & Quality${NC}"
    print_cmd "  test               Run test suite"
    print_cmd "  lint               Run code quality checks"
    echo ""

    echo "${GREEN}Cleanup${NC}"
    print_cmd "  clean              Clean environment and rebuild"
    echo ""

    echo "${YELLOW}Examples:${NC}"
    print_cmd "  bash scripts/help.sh dev"
    print_cmd "  bash scripts/help.sh test"
    echo ""
    exit 0
fi

# Show specific help
case "$1" in

    dev)
        print_header "Dev - Run Development Server"
        echo ""
        echo "${YELLOW}Command:${NC}"
        print_cmd "  bash scripts/dev.sh"
        echo ""
        echo "${YELLOW}What it does:${NC}"
        echo "  • Activates virtual environment"
        echo "  • Sets debug variables"
        echo "  • Runs with auto-reload (if watchdog installed)"
        echo "  • Watch for file changes automatically"
        echo ""
        echo "${YELLOW}When to use:${NC}"
        echo "  • During active development"
        echo "  • Quick testing of changes"
        echo ""
        echo "${YELLOW}For auto-reload, install:${NC}"
        print_cmd "  pip install watchdog"
        echo ""
        ;;

    dev-docker)
        print_header "Docker Dev - Run in Docker Container"
        echo ""
        echo "${YELLOW}Command:${NC}"
        print_cmd "  bash scripts/docker-dev.sh [PORT]"
        echo ""
        echo "${YELLOW}Examples:${NC}"
        print_cmd "  bash scripts/docker-dev.sh         # Default port 8000"
        print_cmd "  bash scripts/docker-dev.sh 8001    # Custom port"
        echo ""
        echo "${YELLOW}What it does:${NC}"
        echo "  • Builds Docker image"
        echo "  • Runs container with volume mounts"
        echo "  • Maps data directory for live updates"
        echo "  • Sets all environment variables"
        echo ""
        echo "${YELLOW}When to use:${NC}"
        echo "  • Testing Docker build"
        echo "  • Testing in containerized environment"
        echo "  • Before deployment"
        echo ""
        ;;

    debug)
        print_header "Debug - Advanced Debugging Mode"
        echo ""
        echo "${YELLOW}Command:${NC}"
        print_cmd "  bash scripts/debug.sh"
        echo ""
        echo "${YELLOW}What it does:${NC}"
        echo "  • Validates all configuration files"
        echo "  • Checks Python syntax"
        echo "  • Verifies imports"
        echo "  • Opens interactive Python shell"
        echo "  • Provides debugging options menu"
        echo ""
        echo "${YELLOW}Debug options provided:${NC}"
        print_cmd "  python3 -v src/main.py              # Verbose output"
        print_cmd "  python3 -m pdb src/main.py          # Python debugger"
        print_cmd "  python3 -m cProfile ... src/main.py # Profiling"
        print_cmd "  python3 src/main.py                 # Normal run"
        print_cmd "  python3 -i src/main.py              # Interactive"
        echo ""
        echo "${YELLOW}When to use:${NC}"
        echo "  • Debugging issues"
        echo "  • Performance analysis"
        echo "  • Interactive testing"
        echo ""
        ;;

    test)
        print_header "Test - Run Test Suite"
        echo ""
        echo "${YELLOW}Command:${NC}"
        print_cmd "  bash scripts/test.sh"
        echo ""
        echo "${YELLOW}Tests included:${NC}"
        echo "  • Python syntax validation"
        echo "  • JSON file validation"
        echo "  • Configuration validation"
        echo "  • Import checks"
        echo "  • Dependency verification"
        echo ""
        echo "${YELLOW}When to use:${NC}"
        echo "  • Before committing"
        echo "  • Before deployment"
        echo "  • After making changes"
        echo ""
        ;;

    lint)
        print_header "Lint - Code Quality Check"
        echo ""
        echo "${YELLOW}Command:${NC}"
        print_cmd "  bash scripts/lint.sh"
        echo ""
        echo "${YELLOW}Checks include:${NC}"
        echo "  • Python syntax validation"
        echo "  • JSON file validation"
        echo "  • Optional: pylint (if installed)"
        echo "  • Optional: vulture dead code (if installed)"
        echo ""
        echo "${YELLOW}Optional linters:${NC}"
        print_cmd "  pip install pylint vulture"
        echo ""
        echo "${YELLOW}When to use:${NC}"
        echo "  • Before committing code"
        echo "  • Regular code quality checks"
        echo "  • Before pull requests"
        echo ""
        ;;

    clean)
        print_header "Clean - Clean Development Environment"
        echo ""
        echo "${YELLOW}Command:${NC}"
        print_cmd "  bash scripts/clean.sh"
        echo ""
        echo "${YELLOW}Removes:${NC}"
        echo "  • Virtual environment (venv/)"
        echo "  • Python cache (__pycache__, .pyc)"
        echo "  • Docker containers and images"
        echo "  • Temporary files"
        echo ""
        echo "${YELLOW}⚠️  WARNING:${NC} This is destructive!"
        echo "   Will ask for confirmation before deleting."
        echo ""
        echo "${YELLOW}When to use:${NC}"
        echo "  • Starting fresh"
        echo "  • Fixing environment issues"
        echo "  • Before archiving project"
        echo ""
        ;;

    *)
        echo "${YELLOW}Unknown command: $1${NC}"
        echo "Use 'bash scripts/help.sh --help' for available commands"
        exit 1
        ;;
esac

echo ""

