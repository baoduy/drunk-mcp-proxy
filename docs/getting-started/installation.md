# Installation Guide

This guide covers all the different ways to install and run drunk-mcp-proxy.

## Prerequisites

### System Requirements

- **Operating System**: Linux, macOS, or Windows
- **Python**: 3.10 or higher
- **Docker**: 20.10+ (for Docker installation)
- **Docker Compose**: 2.0+ (for Docker Compose installation)

### Hardware Requirements

**Minimum**:
- CPU: 1 core
- RAM: 512 MB
- Disk: 100 MB

**Recommended**:
- CPU: 2+ cores
- RAM: 2 GB
- Disk: 1 GB

## Installation Methods

### Method 1: Docker Compose (Recommended)

Docker Compose is the recommended method for most users. It provides the easiest setup with all dependencies included.

**Step 1: Clone the repository**

```bash
git clone https://github.com/baoduy/drunk-mcp-proxy.git
cd drunk-mcp-proxy
```

**Step 2: Review configuration**

The repository includes sample configuration files in the `data/` directory:
- `data/config.json` - Service proxy configurations
- `data/auth.json` - Authentication configurations (optional)
- `data/llm.json` - LLM provider configurations (optional)

**Step 3: Start the services**

```bash
docker-compose up -d
```

**Step 4: Verify installation**

```bash
# Check container status
docker-compose ps

# Check health endpoint
curl http://localhost:9123/health

# View logs
docker-compose logs -f
```

### Method 2: Docker

For users who prefer Docker without Compose.

**Step 1: Build the image**

```bash
git clone https://github.com/baoduy/drunk-mcp-proxy.git
cd drunk-mcp-proxy
docker build -t drunk-mcp-proxy:latest .
```

**Step 2: Create configuration directory**

```bash
mkdir -p ./data
# Copy sample configurations
cp data/*.json ./data/
```

**Step 3: Run the container**

```bash
docker run -d \
  --name mcp-proxy \
  -p 9123:9123 \
  -v $(pwd)/data:/mcp_proxy/data \
  -e FASTMCP_LOG_LEVEL=INFO \
  drunk-mcp-proxy:latest
```

**Step 4: Verify installation**

```bash
docker ps
docker logs mcp-proxy
curl http://localhost:9123/health
```

### Method 3: Python Virtual Environment

For local development or when Docker isn't available.

**Step 1: Install Python dependencies**

```bash
# Clone repository
git clone https://github.com/baoduy/drunk-mcp-proxy.git
cd drunk-mcp-proxy

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install package and dependencies
pip install -e ".[dev]"
```

**Step 2: Configure environment**

```bash
# Copy sample .env file
cp .env.sample .env

# Edit .env file with your settings
nano .env  # or your preferred editor
```

**Step 3: Run the server**

```bash
# Ensure virtual environment is activated
python src/main.py
```

**Step 4: Verify installation**

```bash
curl http://localhost:9123/health
```

### Method 4: System-wide Python Installation

**Not recommended for production**, but useful for testing.

```bash
# Clone repository
git clone https://github.com/baoduy/drunk-mcp-proxy.git
cd drunk-mcp-proxy

# Install dependencies
pip install -e .

# Run server
python src/main.py
```

## Post-Installation Configuration

### Basic Configuration

1. **Edit `data/config.json`** to configure your MCP and OpenAPI services:

```json
[
  {
    "path": "/",
    "spec_file": "mcp/mcp.json",
    "spec_type": "mcp",
    "base_url": null
  }
]
```

2. **Set environment variables** (optional):

```bash
export FASTMCP_HOST=0.0.0.0
export FASTMCP_PORT=9123
export FASTMCP_LOG_LEVEL=INFO
```

3. **Configure authentication** (optional):

Edit `data/auth.json`:

```json
{
  "defaultProvider": "jwt",
  "jwt": {
    "secret": "your-secret-key",
    "algorithm": "HS256"
  }
}
```

### Verify Installation

Run these commands to verify everything is working:

```bash
# Check health endpoint
curl http://localhost:9123/health
# Expected: {"status": "healthy"}

# List available tools (if you have services configured)
curl -X POST http://localhost:9123/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

## Platform-Specific Notes

### Linux

- Use Docker installation for best compatibility
- Ensure Python 3.10+ is installed: `python3 --version`
- May need `sudo` for Docker commands

### macOS

- Docker Desktop for Mac is recommended
- Python 3.10+ available via Homebrew: `brew install python@3.10`
- Use `python3` instead of `python` in commands

### Windows

- Docker Desktop for Windows required
- Use PowerShell or WSL2 for best experience
- Virtual environment activation: `venv\Scripts\activate`
- Use `py` or `python` command instead of `python3`

#### WSL2 (Recommended for Windows)

```bash
# Install WSL2 if not already installed
wsl --install

# Use Ubuntu and follow Linux instructions
wsl
```

## Troubleshooting Installation

### Docker Issues

**Problem**: Cannot connect to Docker daemon
```bash
# Solution: Start Docker service
sudo systemctl start docker  # Linux
# Or start Docker Desktop (macOS/Windows)
```

**Problem**: Port 9123 already in use
```bash
# Solution: Change port in docker-compose.yml or use different port
docker run -p 8080:9123 drunk-mcp-proxy
```

### Python Issues

**Problem**: Python version too old
```bash
# Check version
python3 --version

# Install Python 3.10+ using your package manager
# Ubuntu/Debian:
sudo apt install python3.10

# macOS:
brew install python@3.10
```

**Problem**: Missing dependencies
```bash
# Reinstall dependencies
pip install --force-reinstall -e ".[dev]"
```

### Permission Issues

**Problem**: Permission denied errors
```bash
# Linux: Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Or run with sudo (not recommended)
sudo docker-compose up -d
```

## Upgrading

### Docker Compose

```bash
cd drunk-mcp-proxy
git pull
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Docker

```bash
cd drunk-mcp-proxy
git pull
docker stop mcp-proxy
docker rm mcp-proxy
docker build -t drunk-mcp-proxy:latest .
docker run -d --name mcp-proxy -p 9123:9123 \
  -v $(pwd)/data:/mcp_proxy/data \
  drunk-mcp-proxy:latest
```

### Python Virtual Environment

```bash
cd drunk-mcp-proxy
git pull
source venv/bin/activate
pip install --upgrade -e ".[dev]"
```

## Next Steps

- [Quick Start Guide](quick-start.md) - Get your first proxy running
- [First Steps](first-steps.md) - Learn the basics
- [Configuration Files](../configuration/config-files.md) - Detailed configuration reference

## Getting Help

- [Troubleshooting Guide](../development/troubleshooting.md)
- [GitHub Issues](https://github.com/baoduy/drunk-mcp-proxy/issues)
- [Discussions](https://github.com/baoduy/drunk-mcp-proxy/discussions)
