#!/bin/bash
# Test script for drunk-mcp-proxy

set -e

echo "======================================"
echo "Testing drunk-mcp-proxy"
echo "======================================"
echo ""

# Test 1: Python syntax check
echo "✓ Test 1: Python syntax check"
python3 -m py_compile src/main.py src/auth.py
echo "  ✓ Source files syntax is valid"
echo ""

# Test 2: Config file validation
echo "✓ Test 2: Config file validation"
if [ -f config.json ]; then
    python3 -m json.tool config.json > /dev/null
    echo "  ✓ config.json is valid JSON"
else
    echo "  ✗ config.json not found"
    exit 1
fi
echo ""

# Test 3: Example config validation
echo "✓ Test 3: Example config validation"
if [ -f config.example.json ]; then
    python3 -m json.tool config.example.json > /dev/null
    echo "  ✓ config.example.json is valid JSON"
else
    echo "  ✗ config.example.json not found"
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
