# Troubleshooting Guide

Common issues and solutions for drunk-mcp-proxy.

## Server Startup Issues

### Server Won't Start

**Symptom**: Server fails to start with error messages

**Common Causes & Solutions**:

1. **Port already in use**
   ```bash
   # Check what's using the port
   lsof -i :9123  # macOS/Linux
   netstat -ano | findstr :9123  # Windows
   
   # Solution: Use different port
   export FASTMCP_PORT=8080
   # Or kill the process using the port
   kill -9 <PID>
   ```

2. **Missing configuration files**
   ```bash
   # Error: FileNotFoundError: config.json
   
   # Check files exist
   ls -la data/config.json data/auth.json
   
   # Create from samples
   cp data/config.json.sample data/config.json
   ```

3. **Invalid JSON configuration**
   ```bash
   # Validate JSON
   cat data/config.json | python -m json.tool
   
   # Check schema validation
   # Server logs will show validation errors
   ```

4. **Python version incompatibility**
   ```bash
   # Check Python version
   python --version  # Must be 3.10+
   
   # Install correct version
   # Ubuntu/Debian:
   sudo apt install python3.10
   # macOS:
   brew install python@3.10
   ```

### Import Errors

**Symptom**: `ModuleNotFoundError` or `ImportError`

**Solutions**:

1. **Reinstall package**
   ```bash
   pip install --force-reinstall -e ".[dev]"
   ```

2. **Check virtual environment**
   ```bash
   which python  # Should point to venv
   source venv/bin/activate  # Activate if not active
   ```

3. **Install missing dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration Issues

### Environment Variables Not Working

**Symptom**: Configuration not loading from environment

**Solutions**:

1. **Check variable is exported**
   ```bash
   echo $FASTMCP_PORT  # Should show value
   export FASTMCP_PORT=9123  # Set if empty
   ```

2. **Check .env file**
   ```bash
   # .env file must be in project root
   cat .env
   
   # No quotes needed for values
   FASTMCP_PORT=9123  # Correct
   FASTMCP_PORT="9123"  # Also works but not necessary
   ```

3. **Docker environment**
   ```bash
   # Check container environment
   docker exec mcp-proxy env | grep FASTMCP
   
   # Pass environment in docker-compose.yml
   environment:
     - FASTMCP_PORT=9123
   ```

### Variable Substitution Not Working

**Symptom**: `$VAR_NAME` appears literally in logs

**Solutions**:

1. **Check variable is set**
   ```bash
   # Variable must be set before server starts
   export AZURE_CLIENT_ID=your-value
   ```

2. **Use correct syntax**
   ```json
   {
     "client_id": "$AZURE_CLIENT_ID",      // Correct
     "tenant_id": "${AZURE_TENANT_ID}",    // Also correct
     "value": "$$NOT_SUBSTITUTED"           // $$ escapes $
   }
   ```

3. **Check logs for substitution errors**
   ```bash
   # Enable debug logging
   export FASTMCP_LOG_LEVEL=DEBUG
   python src/main.py
   # Look for "Environment variable resolution" logs
   ```

## Authentication Issues

### JWT Authentication Failing

**Symptom**: `401 Unauthorized` with JWT token

**Solutions**:

1. **Check JWKS URI is accessible**
   ```bash
   curl https://auth.example.com/.well-known/jwks.json
   ```

2. **Verify issuer and audience**
   ```bash
   # Decode JWT to check claims
   # Use jwt.io or:
   python -c "import jwt; print(jwt.decode('YOUR_TOKEN', options={'verify_signature': False}))"
   
   # Check iss (issuer) and aud (audience) match config
   ```

3. **Check clock skew**
   ```bash
   # Ensure system time is correct
   date
   # Sync if needed
   sudo ntpdate -s time.nist.gov  # Linux
   ```

4. **Enable auth debug logging**
   ```python
   # In auth.json
   {
     "defaultProvider": "jwt",
     "jwt": {
       "debug": true,  // Enable debug mode
       ...
     }
   }
   ```

### OAuth Flow Failing

**Symptom**: OAuth redirect or token exchange fails

**Solutions**:

1. **Check redirect URI**
   ```bash
   # Must match exactly in OAuth provider config
   # Including protocol (https vs http) and trailing slash
   BASE_URL=https://proxy.example.com  # No trailing slash
   ```

2. **Verify client credentials**
   ```bash
   # Test token endpoint manually
   curl -X POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token \
     -d "grant_type=client_credentials" \
     -d "client_id=YOUR_CLIENT_ID" \
     -d "client_secret=YOUR_CLIENT_SECRET" \
     -d "scope=https://api.example.com/.default"
   ```

3. **Check scopes**
   ```json
   {
     "scopes": ["https://api.example.com/.default"]  // Must match API
   }
   ```

### Pass-Through Auth Not Working

**Symptom**: Backend receives no auth header

**Solutions**:

1. **Check authorization header format**
   ```bash
   # Must be Bearer token
   Authorization: Bearer eyJhbGc...
   
   # Not:
   Authorization: eyJhbGc...  // Missing "Bearer"
   ```

2. **Enable pass_through in config**
   ```json
   {
     "path": "/api",
     "auth": {
       "pass_through": true  // Must be set
     }
   }
   ```

3. **Check MCP context**
   ```python
   # In logs, look for:
   # "Token extracted from MCP context" (pass-through working)
   # "No token in MCP context" (pass-through not working)
   ```

## Docker Issues

### Container Won't Start

**Symptom**: Docker container exits immediately

**Solutions**:

1. **Check logs**
   ```bash
   docker logs mcp-proxy
   docker-compose logs mcp-proxy
   ```

2. **Check health status**
   ```bash
   docker ps -a  # Check container status
   docker inspect mcp-proxy | grep -A 10 Health
   ```

3. **Verify volume mounts**
   ```bash
   # Check config is accessible
   docker exec mcp-proxy ls -la /mcp_proxy/data/
   
   # Fix permissions if needed
   chmod -R 755 data/
   ```

### Docker Compose Issues

**Symptom**: Services not communicating

**Solutions**:

1. **Check network**
   ```bash
   docker-compose ps
   docker network ls
   docker network inspect drunk-mcp-proxy_default
   ```

2. **Use service names**
   ```yaml
   # In docker-compose.yml, use service name
   REDIS_URL: redis://redis:6379  # Not localhost
   ```

3. **Check environment variables**
   ```bash
   docker-compose config  # Show resolved config
   ```

## MCP Protocol Issues

### Tools Not Appearing

**Symptom**: `tools/list` returns empty or unexpected tools

**Solutions**:

1. **Check backend connectivity**
   ```bash
   # Test backend directly
   curl -X POST http://backend:8080/mcp \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
   ```

2. **Verify spec file**
   ```bash
   # Check MCP spec is valid
   cat data/mcp/service.json | python -m json.tool
   ```

3. **Check namespacing**
   ```bash
   # Root path (/) - aggregates all tools
   curl POST http://localhost:9123/mcp -d '{"method": "tools/list", ...}'
   
   # Namespaced - shows only that service's tools
   curl POST http://localhost:9123/stock/mcp -d '{"method": "tools/list", ...}'
   ```

4. **Check logs**
   ```bash
   # Enable debug logging
   export FASTMCP_LOG_LEVEL=DEBUG
   # Look for "Loaded tools from backend" messages
   ```

### Tool Calls Failing

**Symptom**: `tools/call` returns errors

**Solutions**:

1. **Verify tool name**
   ```bash
   # List tools first
   curl -X POST http://localhost:9123/mcp \
     -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
   
   # Use exact tool name
   ```

2. **Check arguments**
   ```json
   {
     "method": "tools/call",
     "params": {
       "name": "exact_tool_name",
       "arguments": {
         "param": "value"  // Must match tool schema
       }
     }
   }
   ```

3. **Test backend directly**
   ```bash
   # Bypass proxy to test backend
   curl -X POST http://backend:8080/mcp \
     -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {...}}'
   ```

## OpenAPI Integration Issues

### OpenAPI Endpoints Not Converted

**Symptom**: No tools generated from OpenAPI spec

**Solutions**:

1. **Verify OpenAPI spec**
   ```bash
   # Validate spec
   # Use swagger-cli or online validator
   npx swagger-cli validate data/openapi/api.yaml
   ```

2. **Check base_url**
   ```json
   {
     "spec_type": "openapi",
     "base_url": "https://api.example.com"  // Must be set for OpenAPI
   }
   ```

3. **Check filters**
   ```json
   {
     "filters": {
       "methods": ["GET"],  // Maybe too restrictive?
       "tags": ["users"]    // Check tags exist in spec
     }
   }
   ```

4. **Enable debug logging**
   ```bash
   export FASTMCP_LOG_LEVEL=DEBUG
   # Look for "Converting OpenAPI operation" messages
   ```

### OpenAPI Requests Failing

**Symptom**: Tools appear but calls fail

**Solutions**:

1. **Check backend URL**
   ```bash
   # Test backend directly
   curl https://api.example.com/endpoint
   ```

2. **Verify authentication**
   ```json
   {
     "auth": {
       "pass_through": true,  // or
       "azure": { ... }       // Ensure correct auth configured
     }
   }
   ```

3. **Check parameter mapping**
   ```bash
   # Enable debug to see request transformation
   # Look for "Mapping MCP params to HTTP request" logs
   ```

## Performance Issues

### Slow Response Times

**Solutions**:

1. **Enable token caching**
   ```bash
   MCP_OAUTH_STORAGE_TYPE=redis  # Or disk
   FASTMCP_OAUTH_STORAGE_ENCRYPTION_KEY=<key>
   ```

2. **Check backend performance**
   ```bash
   # Time backend directly
   time curl http://backend/mcp -d '...'
   ```

3. **Enable rate limiting**
   ```bash
   FASTMCP_RATE_LIMIT_ENABLED=true
   FASTMCP_RATE_LIMIT_REQUESTS=100
   ```

### High Memory Usage

**Solutions**:

1. **Limit connections**
   ```python
   # In httpx client config
   limits = httpx.Limits(max_connections=100)
   ```

2. **Use Redis for token caching**
   ```bash
   # Instead of in-memory
   MCP_OAUTH_STORAGE_TYPE=redis
   ```

## Network Issues

### CORS Errors

**Symptom**: Browser blocks requests

**Solutions**:

1. **Configure CORS**
   ```bash
   FASTMCP_CORS_ALLOW_ORIGINS=https://app.example.com
   FASTMCP_CORS_ALLOW_METHODS=GET,POST,OPTIONS
   FASTMCP_CORS_ALLOW_HEADERS=Content-Type,Authorization
   FASTMCP_CORS_ALLOW_CREDENTIALS=true
   ```

2. **Check preflight requests**
   ```bash
   # Browser sends OPTIONS first
   curl -X OPTIONS http://localhost:9123/mcp \
     -H "Origin: https://app.example.com" \
     -H "Access-Control-Request-Method: POST" \
     -v
   ```

3. **Allow credentials if needed**
   ```bash
   FASTMCP_CORS_ALLOW_CREDENTIALS=true
   # Also set in client:
   fetch(url, { credentials: 'include' })
   ```

### Connection Refused

**Symptom**: Cannot connect to backend services

**Solutions**:

1. **Check network**
   ```bash
   # From proxy container
   docker exec mcp-proxy curl http://backend:8080/health
   ```

2. **Use correct host**
   ```bash
   # From Docker: use service name
   http://backend:8080  # Not localhost
   
   # For host services from Docker:
   http://host.docker.internal:8080  # macOS/Windows
   http://172.17.0.1:8080  # Linux
   ```

3. **Check firewall**
   ```bash
   # Test connectivity
   telnet backend 8080
   nc -zv backend 8080
   ```

## Getting More Help

If you're still stuck:

1. **Enable debug logging**
   ```bash
   export FASTMCP_LOG_LEVEL=DEBUG
   ```

2. **Check logs carefully**
   ```bash
   # Look for stack traces and error messages
   docker-compose logs -f mcp-proxy
   ```

3. **Create minimal reproduction**
   - Simplify config to minimal case
   - Test each component independently
   - Document exact steps to reproduce

4. **Get help**
   - Search [GitHub Issues](https://github.com/baoduy/drunk-mcp-proxy/issues)
   - Ask in [Discussions](https://github.com/baoduy/drunk-mcp-proxy/discussions)
   - Include: OS, Python version, config (sanitized), logs, error messages

## Related Documentation

- [Development Guide](guide.md)
- [Testing Guide](testing.md)
- [Configuration Reference](../configuration/config-files.md)
- [Environment Variables](../configuration/environment-variables.md)
