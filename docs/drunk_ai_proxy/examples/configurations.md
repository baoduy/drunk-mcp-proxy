# Example Configurations

This document provides ready-to-use configuration examples for common deployment scenarios.

## Basic Configurations

### 1. Single MCP Service

**Use case**: Simple proxy for one MCP backend

**config.yaml**:
```yaml
mcp:
  - path: /
    spec_file: mcp/main.json
    spec_type: mcp
    base_url: null
```

**mcp/main.json**:
```json
{
  "mcpServers": {
    "main-service": {
      "url": "https://mcp-backend.example.com/mcp",
      "transport": "http"
    }
  }
}
```

### 2. Multiple MCP Services with Namespaces

**Use case**: Multiple backend services with isolated namespaces

**config.yaml**:
```yaml
mcp:
  - path: /
    spec_file: mcp/aggregated.json
    spec_type: mcp
  - path: /stock
    spec_file: mcp/stock.json
    spec_type: mcp
    tags:
      - finance
  - path: /wiki
    spec_file: mcp/wiki.json
    spec_type: mcp
    tags:
      - documentation
```

### 3. OpenAPI Service

**Use case**: Expose REST API as MCP tools

**config.yaml**:
```yaml
mcp:
  - path: /petstore
    spec_file: openapi/petstore.yaml
    spec_type: openapi
    base_url: https://petstore3.swagger.io/api/v3
```

### 4. Mixed MCP and OpenAPI

**Use case**: Combine MCP and REST backends

**config.yaml**:
```yaml
mcp:
  - path: /
    spec_file: mcp/core.json
    spec_type: mcp
  - path: /api
    spec_file: openapi/api.yaml
    spec_type: openapi
    base_url: https://api.example.com
```

## Authentication Configurations

### 5. JWT Authentication

**Use case**: Validate JWT tokens from Auth0, Azure AD, etc.

**config.yaml**:
```yaml
auth:
  defaultProvider: jwt
  jwt:
    jwks_uri: https://auth.example.com/.well-known/jwks.json
    issuer: https://auth.example.com/
    audience: mcp-proxy-api
    algorithm: RS256

mcp:
  - path: /
    spec_file: mcp/main.json
    spec_type: mcp
```

**.env**:
```bash
FASTMCP_AUTH_ENABLED=true
JWT_JWKS_URI=https://auth.example.com/.well-known/jwks.json
JWT_ISSUER=https://auth.example.com/
JWT_AUDIENCE=mcp-proxy-api
```

### 6. GitHub OAuth

**Use case**: Allow GitHub users to authenticate

**config.yaml**:
```yaml
auth:
  defaultProvider: github
  github:
    client_id: $GITHUB_CLIENT_ID
    client_secret: $GITHUB_CLIENT_SECRET
    base_url: $BASE_URL
```

**.env**:
```bash
FASTMCP_AUTH_ENABLED=true
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
BASE_URL=https://your-proxy.example.com
```

### 7. Pass-Through Authentication

**Use case**: Forward client tokens to backend APIs

**config.yaml**:
```yaml
mcp:
  - path: /api
    spec_file: openapi/api.yaml
    spec_type: openapi
    base_url: https://api.example.com
    auth:
      pass_through: true
```

### 8. Azure OAuth with Pass-Through Fallback

**Use case**: Try pass-through, fall back to client credentials

**config.yaml**:
```yaml
mcp:
  - path: /api
    spec_file: openapi/api.yaml
    spec_type: openapi
    base_url: https://api.example.com
    auth:
      pass_through: true
      azure:
        client_id: $AZURE_CLIENT_ID
        client_secret: $AZURE_CLIENT_SECRET
        tenant_id: $AZURE_TENANT_ID
        token_url: https://login.microsoftonline.com/$AZURE_TENANT_ID/oauth2/v2.0/token
        scopes:
          - https://api.example.com/.default
```

## Advanced Configurations

### 9. OpenAPI with Filters

**Use case**: Expose only specific endpoints from large OpenAPI spec

**config.yaml**:
```yaml
mcp:
  - path: /api
    spec_file: openapi/full-api.yaml
    spec_type: openapi
    base_url: https://api.example.com
    filters:
      methods:
        - GET
        - POST
      tags:
        - users
        - posts
```

This exposes only GET/POST operations with tags "users" or "posts".

### 10. Skills Directory

**Use case**: Load MCP resources from directory structure

**config.yaml**:
```yaml
mcp:
  - path: /
    spec_file: mcp/main.json
    spec_type: mcp
    skill_dir: skills
```

**Directory structure**:
```
data/
└── skills/
    ├── math/
    │   ├── calculator.py
    │   └── geometry.py
    └── text/
        ├── summarizer.py
        └── translator.py
```

### 11. Multiple Auth Providers

**Use case**: Support multiple authentication methods

**config.yaml**:
```yaml
auth:
  defaultProvider: jwt
  jwt:
    jwks_uri: $JWT_JWKS_URI
    issuer: $JWT_ISSUER
    audience: $JWT_AUDIENCE
  github:
    client_id: $GITHUB_CLIENT_ID
    client_secret: $GITHUB_CLIENT_SECRET
    base_url: $BASE_URL
  inMemory:
    users:
      admin: $ADMIN_PASSWORD
      user: $USER_PASSWORD
```

## Production Configurations

### 12. Production with CORS and Rate Limiting

**.env**:
```bash
# Server
FASTMCP_SERVER_NAME=production-mcp-proxy
FASTMCP_HOST=0.0.0.0
FASTMCP_PORT=9123
FASTMCP_LOG_LEVEL=WARNING

# CORS
FASTMCP_CORS_ALLOW_ORIGINS=https://app.example.com,https://admin.example.com
FASTMCP_CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,OPTIONS
FASTMCP_CORS_ALLOW_HEADERS=Content-Type,Authorization,X-Request-ID
FASTMCP_CORS_ALLOW_CREDENTIALS=true

# Auth
FASTMCP_AUTH_ENABLED=true

# Rate Limiting
FASTMCP_RATE_LIMIT_ENABLED=true
FASTMCP_RATE_LIMIT_REQUESTS=100
FASTMCP_RATE_LIMIT_WINDOW_SECONDS=60

# Remote resources
REMOTE_RESOURCE_TTL_HOURS=24
REMOTE_RESOURCE_ALLOWED_EXTENSIONS=.md,.yaml,.yml,.json,.py,.js,.ts
REMOTE_RESOURCE_MAX_SIZE_MB=10
REMOTE_RESOURCE_RETRY_ATTEMPTS=2

# OAuth Storage
MCP_OAUTH_STORAGE_TYPE=redis
FASTMCP_OAUTH_STORAGE_ENCRYPTION_KEY=<your-44-char-fernet-key>
REDIS_URL=redis://:password@redis:6379/0
```

### 13. Remote Resource Bundles

**Use case**: Download prompts/agents/skills files from HTTPS sources at startup.

**config.yaml**:
```yaml
mcp:
  - path: /prompts
    spec_type: mcp
    skill_dir: skills
    prompt_dir: prompts
    agents_dir: agents

remote_resources:
  - name: dotnet_prompt
    to_dir: prompts/dotnet
    paths:
      - https://raw.githubusercontent.com/dotnet/skills/refs/heads/main/plugins/dotnet-data/skills/optimizing-ef-core-queries/SKILL.md

  - name: dotnet_agent
    to_dir: agents/dotnet
    paths:
      - https://raw.githubusercontent.com/dotnet/skills/refs/heads/main/plugins/dotnet-data/agents/ef-core-agent/agent.yaml

  - name: dotnet_skills
    to_dir: skills/dotnet
    paths:
      - https://raw.githubusercontent.com/dotnet/skills/refs/heads/main/plugins/dotnet-data/codebases/ef-core-codebase/codebase.yaml
```

### 14. Docker Compose Production Setup

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  mcp-proxy:
    build: .
    ports:
      - "9123:9123"
    environment:
      - FASTMCP_HOST=0.0.0.0
      - FASTMCP_PORT=9123
      - FASTMCP_LOG_LEVEL=INFO
      - FASTMCP_AUTH_ENABLED=true
      - FASTMCP_CORS_ALLOW_ORIGINS=https://app.example.com
      - MCP_OAUTH_STORAGE_TYPE=redis
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./data:/mcp_proxy/data:ro
    depends_on:
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9123/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    restart: unless-stopped

volumes:
  redis-data:
```

### 15. Kubernetes Deployment

**deployment.yaml**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-proxy
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mcp-proxy
  template:
    metadata:
      labels:
        app: mcp-proxy
    spec:
      containers:
      - name: mcp-proxy
        image: drunk-mcp-proxy:latest
        ports:
        - containerPort: 9123
        env:
        - name: FASTMCP_HOST
          value: "0.0.0.0"
        - name: FASTMCP_PORT
          value: "9123"
        - name: FASTMCP_AUTH_ENABLED
          value: "true"
        - name: AZURE_CLIENT_ID
          valueFrom:
            secretKeyRef:
              name: azure-secrets
              key: client-id
        - name: AZURE_CLIENT_SECRET
          valueFrom:
            secretKeyRef:
              name: azure-secrets
              key: client-secret
        volumeMounts:
        - name: config
          mountPath: /mcp_proxy/data
          readOnly: true
        livenessProbe:
          httpGet:
            path: /health
            port: 9123
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 9123
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: config
        configMap:
          name: mcp-proxy-config
---
apiVersion: v1
kind: Service
metadata:
  name: mcp-proxy
spec:
  selector:
    app: mcp-proxy
  ports:
  - port: 9123
    targetPort: 9123
  type: LoadBalancer
```

## Development Configurations

### 16. Development with Debug Logging

**.env**:
```bash
FASTMCP_HOST=localhost
FASTMCP_PORT=9123
FASTMCP_LOG_LEVEL=DEBUG
FASTMCP_CONFIG_DIR=./data
FASTMCP_CORS_ALLOW_ORIGINS=*
FASTMCP_AUTH_ENABLED=false
FASTMCP_RATE_LIMIT_ENABLED=false
```

### 17. Testing Configuration

**config.yaml**:
```yaml
auth:
  defaultProvider: inMemory
  inMemory:
    users:
      testuser: testpass

mcp:
  - path: /
    spec_file: mcp/test.json
    spec_type: mcp
```

## Complete Real-World Example

### 18. Enterprise Setup

**config.yaml**:
```yaml
auth:
  defaultProvider: azure
  azure:
    client_id: $AZURE_CLIENT_ID
    client_secret: $AZURE_CLIENT_SECRET
    tenant_id: $AZURE_TENANT_ID
  jwt:
    jwks_uri: https://login.microsoftonline.com/$AZURE_TENANT_ID/discovery/keys
    issuer: https://sts.windows.net/$AZURE_TENANT_ID/
    audience: api://$AZURE_CLIENT_ID

mcp:
  - path: /
    spec_file: mcp/core.json
    spec_type: mcp
    skill_dir: skills
    tags:
      - core
      - public
  - path: /internal
    spec_file: mcp/internal.json
    spec_type: mcp
    tags:
      - internal
  - path: /trading
    spec_file: openapi/trading-api.yaml
    spec_type: openapi
    base_url: https://trading.example.com/api/v1
    filters:
      methods:
        - GET
        - POST
      tags:
        - Orders
        - Positions
    auth:
      pass_through: true
      azure:
        client_id: $TRADING_CLIENT_ID
        client_secret: $TRADING_CLIENT_SECRET
        tenant_id: $AZURE_TENANT_ID
        token_url: https://login.microsoftonline.com/$AZURE_TENANT_ID/oauth2/v2.0/token
        scopes:
          - https://trading.example.com/.default
    tags:
      - trading
      - internal
  - path: /public-api
    spec_file: openapi/public-api.yaml
    spec_type: openapi
    base_url: https://api.example.com
    tags:
      - public
```

**.env**:
```bash
# Server
FASTMCP_SERVER_NAME=enterprise-mcp-proxy
FASTMCP_HOST=0.0.0.0
FASTMCP_PORT=9123
FASTMCP_LOG_LEVEL=INFO

# Auth
FASTMCP_AUTH_ENABLED=true
AZURE_CLIENT_ID=12345678-1234-1234-1234-123456789abc
AZURE_CLIENT_SECRET=<secret>
AZURE_TENANT_ID=87654321-4321-4321-4321-cba987654321

# Trading API
TRADING_CLIENT_ID=<trading-client-id>
TRADING_CLIENT_SECRET=<trading-secret>

# CORS
FASTMCP_CORS_ALLOW_ORIGINS=https://app.example.com,https://admin.example.com
FASTMCP_CORS_ALLOW_CREDENTIALS=true

# Rate Limiting
FASTMCP_RATE_LIMIT_ENABLED=true
FASTMCP_RATE_LIMIT_REQUESTS=100
FASTMCP_RATE_LIMIT_WINDOW_SECONDS=60

# OAuth Storage
MCP_OAUTH_STORAGE_TYPE=redis
FASTMCP_OAUTH_STORAGE_ENCRYPTION_KEY=<44-char-fernet-key>
REDIS_URL=redis://:password@redis.example.com:6379/0
```

## Related Documentation

- [Configuration Files](../configuration/config-files.md)
- [Environment Variables](../configuration/environment-variables.md)
- [Authentication Overview](../features/authentication/overview.md)
- [Deployment Guide](../deployment/docker.md)
