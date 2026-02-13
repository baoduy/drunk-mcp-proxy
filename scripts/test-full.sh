h#!/bin/bash
# Test script for drunk-mcp-proxy

set -e

echo "======================================"
echo "Testing drunk-mcp-proxy"
echo "======================================"
echo ""

# Test 1: Python syntax check
echo "✓ Test 1: Python syntax check"
python3 -m py_compile src/main.py
echo "  ✓ Source files syntax is valid"
echo ""

# Test 2: Config file validation
echo "✓ Test 2: Config file validation"
# Create data directory and copy config if needed for testing
mkdir -p data
if [ ! -f data/mcp.json ] && [ -f mcp.json ]; then
    cp mcp.json data/mcp.json
fi
if [ -f data/mcp.json ]; then
    python3 -m json.tool data/mcp.json > /dev/null
    echo "  ✓ data/mcp.json is valid JSON"
elif [ -f mcp.json ]; then
    python3 -m json.tool mcp.json > /dev/null
    echo "  ✓ mcp.json is valid JSON"
else
    echo "  ✗ mcp.json not found"
    exit 1
fi
echo ""

# Test 3: Example config validation
echo "✓ Test 3: Example config validation"
if [ -f mcp.example.json ]; then
    python3 -m json.tool mcp.example.json > /dev/null
    echo "  ✓ mcp.example.json is valid JSON"
else
    echo "  ✗ mcp.example.json not found"
    exit 1
fi
echo ""

# Test 4: Docker build
echo "✓ Test 4: Docker build"
docker build -t drunk-mcp-proxy:test . > /tmp/docker-build.log 2>&1
if [ $? -eq 0 ]; then
    echo "  ✓ Docker image built successfully"
else
    echo "  ✗ Docker build failed"
    tail -20 /tmp/docker-build.log
    exit 1
fi
echo ""

# Test 5: Docker container test
echo "✓ Test 5: Docker container test"
docker run --rm -e PYTHONPATH=/app/src drunk-mcp-proxy:test python -c "import sys; sys.path.insert(0, '/app/src'); import main; print('Module imports OK')" > /tmp/docker-test.log 2>&1
if [ $? -eq 0 ]; then
    echo "  ✓ Container runs and imports work"
else
    echo "  ✗ Container test failed"
    cat /tmp/docker-test.log
    exit 1
fi
echo ""

# Test 6: Docker compose config validation
echo "✓ Test 6: Docker compose validation"
docker compose config > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "  ✓ docker-compose.yml is valid"
else
    echo "  ✗ docker-compose.yml validation failed"
    exit 1
fi
echo ""

echo "======================================"
echo "All tests passed! ✓"
echo "======================================"
