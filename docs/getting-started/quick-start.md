# Quick Start Guide

Get drunk-mcp-proxy up and running in 5 minutes!

## Prerequisites

- Docker and Docker Compose installed, OR
- Python 3.10+ installed

## 5-Minute Setup

### Step 1: Get the Code (30 seconds)

```bash
git clone https://github.com/baoduy/drunk-mcp-proxy.git
cd drunk-mcp-proxy
```

### Step 2: Start with Docker Compose (1 minute)

```bash
docker-compose up -d
```

That's it! The server is now running.

### Step 3: Verify It's Working (30 seconds)

```bash
# Check health status
curl http://localhost:9123/health

# Expected response:
# {"status": "healthy"}
```

### Step 4: Test MCP Protocol (1 minute)

```bash
# List available tools
curl -X POST http://localhost:9123/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'
```

You should see a list of available MCP tools from your configured services.

## What Just Happened?

The default setup:

1. **Started the proxy server** on port 9123
2. **Loaded configuration** from `data/config.yaml`
3. **Configured sample services** (if using default config)
4. **Enabled health check** at `/health`

## Your First Configuration

The default `data/config.yaml` includes example services. Let's understand it:

```yaml
mcp:
  - path: /
    spec_file: mcp/mcp.json
    spec_type: mcp
    base_url: null
```

**What this means:**
- `path`: "/" - Services are mounted at the root path
- `spec_file`: "mcp/mcp.json" - MCP specification file location (relative to CONFIG_DIR)
- `spec_type`: "mcp" - This is an MCP service (not OpenAPI)
- `base_url`: null - Not needed for MCP services

## Next Steps

### Option A: Add More MCP Services

Edit `data/config.yaml`:

```yaml
mcp:
  - path: /
    spec_file: mcp/mcp.json
    spec_type: mcp
  - path: /stock
    spec_file: mcp/stock.mcp.json
    spec_type: mcp
  - path: /wiki
    spec_file: mcp/wiki.mcp.json
    spec_type: mcp
```

Restart the service:
```bash
docker-compose restart
```

### Option B: Add an OpenAPI Service

```yaml
mcp:
  - path: /
    spec_file: mcp/mcp.json
    spec_type: mcp
  - path: /petstore
    spec_file: openapi/petstore.yaml
    spec_type: openapi
    base_url: "https://petstore3.swagger.io/api/v3"
```

### Option C: Enable Authentication

Edit the `auth` section in `data/config.yaml`:

```yaml
auth:
  defaultProvider: jwt
  jwt:
    base_url: null
    jwks_uri: "https://login.microsoftonline.com/common/discovery/keys"
    issuer: "https://sts.windows.net/YOUR_TENANT_ID/"
    audience: "api://your-api-id"
```

Enable auth in `.env` or docker-compose.yml:
```bash
FASTMCP_AUTH_ENABLED=true
```

## Common Quick Configurations

### Debug Mode

For development, enable debug logging:

```bash
# In .env or docker-compose.yml
FASTMCP_LOG_LEVEL=DEBUG
```

### Change Port

```bash
# In docker-compose.yml
ports:
  - "8080:9123"  # Host port 8080, container port 9123
```

Or with environment variable:
```bash
FASTMCP_PORT=8080
```

### Configure CORS

For web client access:

```bash
# Allow all origins (development only!)
FASTMCP_CORS_ALLOW_ORIGINS=*

# Allow specific origins (production)
FASTMCP_CORS_ALLOW_ORIGINS=https://app.example.com,https://admin.example.com
```

## Testing Your Setup

### Test 1: Health Check

```bash
curl http://localhost:9123/health
```

**Success**: `{"status": "healthy"}`

### Test 2: List Tools

```bash
curl -X POST http://localhost:9123/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

**Success**: JSON response with tools array

### Test 3: Call a Tool

```bash
curl -X POST http://localhost:9123/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "your-tool-name",
      "arguments": {}
    },
    "id": 2
  }'
```

## Troubleshooting Quick Issues

### Issue: Port already in use

```bash
# Check what's using the port
lsof -i :9123  # macOS/Linux
netstat -ano | findstr :9123  # Windows

# Change port in docker-compose.yml
ports:
  - "8080:9123"
```

### Issue: Container won't start

```bash
# Check logs
docker-compose logs

# Rebuild
docker-compose down
docker-compose up -d --build
```

### Issue: Config not loading

```bash
# Check config file exists
ls -la data/config.yaml

# Validate YAML
python -c "import yaml; yaml.safe_load(open('data/config.yaml'))"

# Check container has access
docker-compose exec mcp-proxy ls -la /mcp_proxy/data/
```

### Issue: Health check fails

```bash
# Check server is running
docker-compose ps

# Check logs for errors
docker-compose logs mcp-proxy

# Test from inside container
docker-compose exec mcp-proxy curl http://localhost:9123/health
```

## Alternative: Local Python Setup

If you don't want to use Docker:

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Run
python src/main.py
```

## What's Next?

Now that you have it running:

1. **Understand the basics**: [First Steps](first-steps.md)
2. **Configure your services**: [Configuration Files](../configuration/config-files.md)
3. **Add authentication**: [Authentication Overview](../features/authentication/overview.md)
4. **Deploy to production**: [Production Setup](../deployment/production.md)

## Getting Help

- **Documentation**: [Full Documentation Index](../INDEX.md)
- **Examples**: [Example Configurations](../examples/configurations.md)
- **Issues**: [GitHub Issues](https://github.com/baoduy/drunk-mcp-proxy/issues)
- **Discussions**: [GitHub Discussions](https://github.com/baoduy/drunk-mcp-proxy/discussions)

---

**🎉 Congratulations!** You now have drunk-mcp-proxy running. Continue to [First Steps](first-steps.md) to learn how to use it effectively.
