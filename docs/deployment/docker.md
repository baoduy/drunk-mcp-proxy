# Docker Deployment Guide

This guide provides comprehensive information for deploying drunk-mcp-proxy using Docker and Docker Compose.

## Table of Contents

- [Quick Start](#quick-start)
- [Docker Image](#docker-image)
- [Docker Compose](#docker-compose-recommended)
- [Configuration](#configuration)
- [Environment Variables](#environment-variables)
- [Volumes](#volumes)
- [Networking](#networking)
- [Health Checks](#health-checks)
- [Multi-Stage Build](#multi-stage-build)
- [Security](#security)
- [Production Deployment](#production-deployment)
- [Kubernetes Integration](#kubernetes-integration)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone the repository:**
```bash
git clone https://github.com/baoduy/drunk-mcp-proxy.git
cd drunk-mcp-proxy
```

2. **Configure services in `data/config.yaml`:**
```yaml
mcp:
  - path: "/"
    spec_file: "mcp/mcp.json"
    spec_type: "mcp"
    base_url: null
```

3. **Create `.env` file (optional):**
```bash
FASTMCP_PORT=9123
FASTMCP_LOG_LEVEL=INFO
FASTMCP_SERVER_NAME=mcp-proxy-server
```

4. **Start the services:**
```bash
docker-compose up -d
```

5. **Verify it's running:**
```bash
curl http://localhost:9123/health
```

### Using Docker

```bash
# Build the image
docker build -t drunk-mcp-proxy:latest .

# Run the container
docker run -d \
  --name mcp-proxy \
  -p 9123:9123 \
  -v $(pwd)/data:/drunk-proxy/data \
  -e FASTMCP_LOG_LEVEL=INFO \
  drunk-mcp-proxy:latest

# Check logs
docker logs -f mcp-proxy

# Check health
curl http://localhost:9123/health
```

## Docker Image

### Image Architecture

The Dockerfile uses a multi-stage build for optimal image size and security:

```dockerfile
# Stage 1: Builder
FROM python:3.14-slim AS builder
- Install build dependencies
- Create virtual environment
- Install Python packages
- Install uv package manager

# Stage 2: Runtime
FROM python:3.14-slim AS runtime
- Copy virtual environment from builder
- Install runtime dependencies (Node.js, npm, curl)
- Create non-root user (appuser)
- Set up application directories
- Configure environment variables
```

### Image Features

1. **Minimal Size**: Multi-stage build removes build tools
2. **Security**: Runs as non-root user (UID 10001)
3. **Python 3.14**: Latest Python version
4. **Node.js Support**: Includes Node.js and npm for MCP servers
5. **Package Managers**: Both pip and uv available
6. **Health Checks**: Built-in health check support

### Building Custom Images

**Basic build:**
```bash
docker build -t drunk-mcp-proxy:latest .
```

**Build for specific platform:**
```bash
docker build --platform linux/amd64 -t drunk-mcp-proxy:amd64 .
docker build --platform linux/arm64 -t drunk-mcp-proxy:arm64 .
```

**Build with custom tag:**
```bash
docker build -t myregistry.com/drunk-mcp-proxy:v1.0.0 .
```

**Build with build arguments:**
```bash
docker build \
  --build-arg TARGETPLATFORM=linux/amd64 \
  -t drunk-mcp-proxy:latest .
```

## Docker Compose (Recommended)

### Basic Configuration

**docker-compose.yml:**
```yaml
services:
  mcp-proxy:
    build: .
    image: drunk-mcp-proxy:latest
    container_name: mcp-proxy-server
    ports:
      - "${FASTMCP_PORT:-9123}:${FASTMCP_PORT:-9123}"
    volumes:
      - ./data:/drunk-proxy/data
      - mcp-pip-cache:/tmp/pip-cache
      - mcp-home-cache:/home/appuser
    env_file:
      - .env
    environment:
      - FASTMCP_ENABLE_OPENAPI=${FASTMCP_ENABLE_OPENAPI:-true}
      - FASTMCP_HOST=0.0.0.0
      - FASTMCP_PORT=${FASTMCP_PORT:-9123}
      - FASTMCP_SERVER_NAME=${FASTMCP_SERVER_NAME:-mcp-proxy-server}
      - FASTMCP_SERVER_VERSION=${FASTMCP_SERVER_VERSION:-1.0.0}
    restart: unless-stopped
    networks:
      - mcp-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9123/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s

networks:
  mcp-network:
    driver: bridge

volumes:
  mcp-pip-cache:
    driver: local
  mcp-home-cache:
    driver: local
```

### With Additional Services

The default `docker-compose.yml` includes additional services:

**MCP Inspector:**
```yaml
  mcp-inspector:
    image: ghcr.io/modelcontextprotocol/inspector:latest
    container_name: mcp-inspector
    ports:
      - "127.0.0.1:6274:6274"
      - "127.0.0.1:6277:6277"
    environment:
      - HOST=0.0.0.0
      - MCP_AUTO_OPEN_ENABLED=false
    restart: unless-stopped
    networks:
      - mcp-network
```

**Open WebUI (Optional):**
```yaml
  openwebui:
    image: ghcr.io/open-webui/open-webui:latest
    container_name: openwebui
    ports:
      - "3000:8080"
    environment:
      - WEBUI_AUTH=false
      - WEBUI_SECRET_KEY=Dj3EFkjbwL9NaLjXTBn7
      - ENABLE_OPENAI_API=true
      - OPENAI_API_BASE_URL=http://mcp-proxy-server:9123/llm/v1
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - openwebui-data:/app/backend/data
    restart: unless-stopped
    networks:
      - mcp-network
```

### Docker Compose Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f mcp-proxy

# Rebuild and start
docker-compose up -d --build

# Restart a service
docker-compose restart mcp-proxy

# Check service status
docker-compose ps

# Remove volumes (careful - deletes data)
docker-compose down -v
```

## Configuration

### Configuration Files

Mount your configuration directory to `/drunk-proxy/data`:

```bash
docker run -d \
  -v $(pwd)/data:/drunk-proxy/data \
  drunk-mcp-proxy:latest
```

**Required files:**
- `data/config.yaml` - Main configuration file (auth, llm, mcp sections)
- `data/mcp/*.mcp.json` - MCP service specifications
- `data/openapi/*.openapi.json` - OpenAPI specifications

**Optional files:**
- `data/skills/` - Markdown-based skills directory
- `.env` - Environment variables

### Configuration Example

**data/config.yaml:**
```yaml
auth:
  enabled: true
  defaultProvider: jwt
  jwt:
    jwks_uri: "https://auth.example.com/.well-known/jwks.json"
    issuer: "https://auth.example.com/"
    audience: "mcp-proxy-api"

llm:
  provider: openai
  api_key: "${OPENAI_API_KEY}"
  model: "gpt-4"

mcp:
  - path: "/"
    spec_file: "mcp/mcp.json"
    spec_type: "mcp"
    base_url: null
  - path: "/api"
    spec_file: "openapi/api.openapi.json"
    spec_type: "openapi"
    base_url: "https://api.example.com"
    auth:
      pass_through: true
```

## Environment Variables

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `FASTMCP_CONFIG_DIR` | `/drunk-proxy/data` | Configuration directory path |
| `FASTMCP_SCHEMA_DIR` | `/drunk-proxy/schemas` | JSON schema directory |
| `FASTMCP_HOST` | `0.0.0.0` | Server bind address |
| `FASTMCP_PORT` | `9123` | Server port |
| `FASTMCP_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `FASTMCP_SERVER_NAME` | `mcp-proxy-server` | Server name |
| `FASTMCP_SERVER_VERSION` | `1.0.0` | Server version |
| `FASTMCP_ENABLE_OPENAPI` | `true` | Enable OpenAPI integration |

### Authentication

| Variable | Description |
|----------|-------------|
| `FASTMCP_SERVER_AUTH` | Auth provider (jwt, github, google, discord, etc.) |
| `JWKS_URI` | JWT JWKS endpoint URL |
| `ISSUER` | JWT issuer |
| `AUDIENCE` | JWT audience |
| `AZURE_CLIENT_ID` | Azure OAuth client ID |
| `AZURE_CLIENT_SECRET` | Azure OAuth client secret |
| `AZURE_TENANT_ID` | Azure tenant ID |
| `FASTMCP_OAUTH_STORAGE_ENCRYPTION_KEY` | OAuth token encryption key |

### CORS Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `FASTMCP_CORS_ALLOW_ORIGINS` | `*` | Allowed origins (comma-separated) |
| `FASTMCP_CORS_ALLOW_METHODS` | `*` | Allowed methods |
| `FASTMCP_CORS_ALLOW_HEADERS` | `*` | Allowed headers |
| `FASTMCP_CORS_ALLOW_CREDENTIALS` | `false` | Allow credentials |

### Package Management

| Variable | Default | Description |
|----------|---------|-------------|
| `PIP_CACHE_DIR` | `/tmp/pip-cache` | pip cache directory |
| `NPM_CONFIG_CACHE` | `/home/appuser/.npm` | npm cache directory |
| `UV_CACHE_DIR` | `/home/appuser/.cache/uv` | uv cache directory |

### Example .env File

```bash
# Server Configuration
FASTMCP_PORT=9123
FASTMCP_LOG_LEVEL=INFO
FASTMCP_SERVER_NAME=mcp-proxy-server
FASTMCP_SERVER_VERSION=1.0.0
FASTMCP_ENABLE_OPENAPI=true

# Authentication (JWT)
FASTMCP_SERVER_AUTH=jwt
JWKS_URI=https://auth.example.com/.well-known/jwks.json
ISSUER=https://auth.example.com/
AUDIENCE=mcp-proxy-api

# Azure OAuth (for backend services)
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id

# CORS
FASTMCP_CORS_ALLOW_ORIGINS=https://your-app.com,https://localhost:3000
FASTMCP_CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,OPTIONS
FASTMCP_CORS_ALLOW_HEADERS=*

# OAuth Token Encryption
FASTMCP_OAUTH_STORAGE_ENCRYPTION_KEY=your-encryption-key-here
```

## Volumes

### Required Volumes

**Configuration Directory:**
```yaml
volumes:
  - ./data:/drunk-proxy/data
```
Contains all configuration files, MCP specs, and OpenAPI specs.

### Recommended Volumes

**pip Cache:**
```yaml
volumes:
  - mcp-pip-cache:/tmp/pip-cache
```
Speeds up Python package installations.

**User Home Cache:**
```yaml
volumes:
  - mcp-home-cache:/home/appuser
```
Caches npm packages, uv tools, and other user data.

### Volume Management

**List volumes:**
```bash
docker volume ls
```

**Inspect volume:**
```bash
docker volume inspect mcp-pip-cache
```

**Remove unused volumes:**
```bash
docker volume prune
```

**Backup configuration:**
```bash
docker run --rm \
  -v drunk-mcp-proxy_mcp-home-cache:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/cache-backup.tar.gz /data
```

## Networking

### Bridge Network

Default network mode for Docker Compose:

```yaml
networks:
  mcp-network:
    driver: bridge
```

**Benefits:**
- Service discovery by name
- Isolated from host network
- Services can communicate internally

**Access services:**
```bash
# From another container
curl http://mcp-proxy-server:9123/health

# From host
curl http://localhost:9123/health
```

### Host Network (Not Recommended)

```bash
docker run -d \
  --network host \
  drunk-mcp-proxy:latest
```

**Use cases:**
- Development only
- Need to access host services directly

### Custom Network

```bash
# Create network
docker network create --driver bridge custom-network

# Run container
docker run -d \
  --network custom-network \
  --name mcp-proxy \
  drunk-mcp-proxy:latest
```

## Health Checks

### Docker Health Check

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:9123/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 5s
```

**Parameters:**
- `interval`: Time between checks (30s)
- `timeout`: Maximum time for check (10s)
- `retries`: Consecutive failures before unhealthy (3)
- `start_period`: Grace period on startup (5s)

### Check Container Health

```bash
# Docker inspect
docker inspect --format='{{.State.Health.Status}}' mcp-proxy

# Docker ps with health
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Health check logs
docker inspect --format='{{json .State.Health}}' mcp-proxy | jq .
```

### Custom Health Check

```bash
# Override in docker run
docker run -d \
  --health-cmd="curl -f http://localhost:9123/health || exit 1" \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  --health-start-period=40s \
  drunk-mcp-proxy:latest
```

## Multi-Stage Build

The Dockerfile uses a multi-stage build for efficiency:

### Stage 1: Builder

```dockerfile
FROM python:3.14-slim AS builder

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir .
```

**Purpose:**
- Install build tools
- Compile Python packages
- Create optimized virtual environment

### Stage 2: Runtime

```dockerfile
FROM python:3.14-slim AS runtime

# Copy only virtual environment
COPY --from=builder /opt/venv /opt/venv

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      nodejs npm curl
```

**Purpose:**
- Minimal runtime image
- No build tools
- Reduced attack surface
- Smaller image size

### Build Optimizations

1. **Layer caching**: Dependencies installed before code
2. **Multi-stage**: Build artifacts separate from runtime
3. **No cache**: `--no-cache-dir` reduces image size
4. **Cleanup**: Remove apt lists and temp files

## Security

### Non-Root User

Container runs as non-root user `appuser` (UID 10001):

```dockerfile
RUN useradd -m -u 10001 appuser
USER appuser
```

**Benefits:**
- Reduced privilege escalation risk
- Container breakout protection
- Compliance with security best practices

### Read-Only Configuration

Mount configuration as read-only:

```yaml
volumes:
  - ./data:/drunk-proxy/data:ro
```

**Prevents:**
- Configuration tampering
- Accidental modifications
- Unauthorized changes

### Secrets Management

**Do not** store secrets in:
- Configuration files
- Environment variables in docker-compose.yml
- Docker images

**Use instead:**
- Docker secrets
- Environment variable files (.env)
- External secret management (Vault, AWS Secrets Manager)

**Example with Docker secrets:**
```yaml
services:
  mcp-proxy:
    secrets:
      - azure_client_secret
    environment:
      - AZURE_CLIENT_SECRET_FILE=/run/secrets/azure_client_secret

secrets:
  azure_client_secret:
    file: ./secrets/azure_client_secret.txt
```

### Network Security

1. **Bind to localhost only** (development):
```yaml
ports:
  - "127.0.0.1:9123:9123"
```

2. **Use reverse proxy** (production):
```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
```

3. **Enable TLS**:
- Terminate TLS at reverse proxy
- Use valid certificates
- Enforce HTTPS

### Image Scanning

Scan images for vulnerabilities:

```bash
# Using Docker Scout
docker scout cves drunk-mcp-proxy:latest

# Using Trivy
trivy image drunk-mcp-proxy:latest

# Using Grype
grype drunk-mcp-proxy:latest
```

## Production Deployment

### Production Docker Compose

```yaml
version: '3.8'

services:
  mcp-proxy:
    image: drunk-mcp-proxy:latest
    container_name: mcp-proxy-production
    restart: always
    ports:
      - "127.0.0.1:9123:9123"
    volumes:
      - ./data:/drunk-proxy/data:ro
      - mcp-pip-cache:/tmp/pip-cache
      - mcp-home-cache:/home/appuser
    environment:
      - FASTMCP_LOG_LEVEL=WARNING
      - FASTMCP_SERVER_NAME=mcp-proxy-production
      - FASTMCP_CORS_ALLOW_ORIGINS=https://app.example.com
      - FASTMCP_SERVER_AUTH=jwt
    env_file:
      - .env.production
    networks:
      - mcp-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9123/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 512M

networks:
  mcp-network:
    driver: bridge

volumes:
  mcp-pip-cache:
  mcp-home-cache:
```

### Production Checklist

- [ ] Use specific image tags (not `latest`)
- [ ] Enable authentication
- [ ] Configure CORS properly
- [ ] Use HTTPS/TLS
- [ ] Set resource limits
- [ ] Configure log rotation
- [ ] Enable health checks
- [ ] Set restart policy
- [ ] Use read-only volumes
- [ ] Scan images for vulnerabilities
- [ ] Set up monitoring
- [ ] Configure backups
- [ ] Test disaster recovery

### Monitoring

**Prometheus metrics** (future enhancement):
```yaml
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    networks:
      - mcp-network
```

**Grafana dashboards** (future enhancement):
```yaml
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
    networks:
      - mcp-network
```

### Logging

**Centralized logging:**
```yaml
logging:
  driver: "syslog"
  options:
    syslog-address: "tcp://logs.example.com:514"
    tag: "mcp-proxy"
```

**Log aggregation:**
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Graylog
- Splunk
- CloudWatch Logs

## Kubernetes Integration

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-proxy
  labels:
    app: mcp-proxy
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
          name: http
        env:
        - name: FASTMCP_LOG_LEVEL
          value: "INFO"
        - name: FASTMCP_SERVER_AUTH
          value: "jwt"
        - name: JWKS_URI
          valueFrom:
            secretKeyRef:
              name: mcp-proxy-secrets
              key: jwks-uri
        volumeMounts:
        - name: config
          mountPath: /drunk-proxy/data
          readOnly: true
        - name: cache
          mountPath: /tmp/pip-cache
        livenessProbe:
          httpGet:
            path: /health
            port: 9123
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 9123
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 2000m
            memory: 2Gi
      volumes:
      - name: config
        configMap:
          name: mcp-proxy-config
      - name: cache
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: mcp-proxy
  labels:
    app: mcp-proxy
spec:
  type: LoadBalancer
  ports:
  - port: 9123
    targetPort: 9123
    protocol: TCP
    name: http
  selector:
    app: mcp-proxy
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-proxy-config
data:
  config.yaml: |
    mcp:
      - path: "/"
        spec_file: "mcp/mcp.json"
        spec_type: "mcp"
---
apiVersion: v1
kind: Secret
metadata:
  name: mcp-proxy-secrets
type: Opaque
stringData:
  jwks-uri: "https://auth.example.com/.well-known/jwks.json"
```

### Helm Chart (Future)

```bash
# Install
helm install mcp-proxy ./charts/drunk-mcp-proxy \
  --set image.tag=v1.0.0 \
  --set auth.enabled=true \
  --set replicaCount=3

# Upgrade
helm upgrade mcp-proxy ./charts/drunk-mcp-proxy \
  --set image.tag=v1.1.0

# Uninstall
helm uninstall mcp-proxy
```

## Troubleshooting

### Container Won't Start

**Check logs:**
```bash
docker logs mcp-proxy
docker-compose logs mcp-proxy
```

**Common issues:**
- Port already in use: Change `FASTMCP_PORT`
- Invalid configuration: Validate YAML syntax
- Missing environment variables: Check `.env` file
- Permission issues: Check volume permissions

### Health Check Failing

**Debug:**
```bash
# Check health endpoint
docker exec mcp-proxy curl -f http://localhost:9123/health

# Check container status
docker inspect --format='{{json .State.Health}}' mcp-proxy | jq .

# View health check logs
docker inspect mcp-proxy | jq '.[0].State.Health.Log'
```

### Configuration Not Loading

**Verify:**
```bash
# Check volume mount
docker inspect mcp-proxy | jq '.[0].Mounts'

# Check file permissions
docker exec mcp-proxy ls -la /drunk-proxy/data

# View configuration
docker exec mcp-proxy cat /drunk-proxy/data/config.yaml
```

### Network Issues

**Test connectivity:**
```bash
# From host
curl http://localhost:9123/health

# From another container
docker exec other-container curl http://mcp-proxy-server:9123/health

# Check network
docker network inspect mcp-network
```

### Performance Issues

**Monitor resources:**
```bash
# Container stats
docker stats mcp-proxy

# Top processes
docker exec mcp-proxy top

# Memory usage
docker exec mcp-proxy free -h
```

**Optimize:**
- Increase resource limits
- Use volume caching
- Enable connection pooling
- Monitor backend services

### Image Build Failures

**Common issues:**
```bash
# Clear build cache
docker builder prune

# Build with no cache
docker build --no-cache -t drunk-mcp-proxy:latest .

# Check Docker version
docker --version

# Check Dockerfile syntax
hadolint Dockerfile
```

## Related Documentation

- [First Steps](../getting-started/first-steps.md) - Getting started guide
- [Configuration Reference](../configuration/) - Detailed configuration
- [API Reference](../api-reference/endpoints.md) - API endpoints
- [Troubleshooting](../troubleshooting/) - Common issues and solutions

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
