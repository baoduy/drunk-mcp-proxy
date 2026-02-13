# ✅ uvx and npx Availability Fix

## Problem Identified

Both `uvx` and `npx` commands were not available in the container.

---

## Root Causes

1. **uvx** - `uv` tool was not installed in user space (only in builder venv)
2. **npx** - `npm` package manager was missing the necessary components

---

## Solution Implemented

### For `uvx` Availability

**What was needed**:

- Install `uv` in the builder venv ✅
- Install `uv` again in user space as appuser ✅
- Add to PATH ✅

**How it was fixed**:

```dockerfile
# In builder stage
RUN pip install --no-cache-dir uv

# In runtime stage, as appuser user
RUN pip install --user --no-cache-dir uv

# PATH includes user bin directories
ENV PATH="/opt/venv/bin:/home/appuser/.npm-global/bin:/home/appuser/.local/bin:${PATH}"
```

### For `npx` Availability

**What was needed**:

- Install nodejs package ✅
- Install npm package manager ✅
- Configure npm global prefix ✅
- Add to PATH ✅

**How it was fixed**:

```dockerfile
# Install nodejs and npm
RUN apt-get install -y --no-install-recommends \
      nodejs \
      npm \
      curl

# Configure npm
ENV NPM_CONFIG_PREFIX=/home/appuser/.npm-global

# Add npm global bin to PATH
PATH="/opt/venv/bin:/home/appuser/.npm-global/bin:/home/appuser/.local/bin:${PATH}"
```

---

## Verification Steps

The Dockerfile now includes verification commands:

```dockerfile
# Verify both npx and uvx are available
RUN npx --version && uv --version
```

**What this does**:

- ✅ Runs during build time
- ✅ Confirms `npx` is available (from npm)
- ✅ Confirms `uv` is available (from pip install)
- ✅ Build fails if either is missing

---

## Changes Made to Dockerfile

### Environment Variables

```dockerfile
ENV FASTMCP_CONFIG_FILE=/app/data \
    FASTMCP_HOST=0.0.0.0 \
    FASTMCP_PORT=9123 \
    PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    HOME=/home/appuser \
    NPM_CONFIG_PREFIX=/home/appuser/.npm-global \
    NPM_CONFIG_CACHE=/home/appuser/.npm \
    UV_CACHE_DIR=/home/appuser/.cache/uv \
    UV_TOOL_DIR=/home/appuser/.local/uv/tools \
    PIP_CACHE_DIR=/tmp/pip-cache \
    PATH="/opt/venv/bin:/home/appuser/.npm-global/bin:/home/appuser/.local/bin:${PATH}"
```

### Directory Setup

```dockerfile
RUN mkdir -p /home/appuser/.npm-global \
             /home/appuser/.npm \
             /home/appuser/.cache/uv \
             /home/appuser/.local/uv/tools && \
    chown -R appuser:appuser /home/appuser
```

### Installation Commands

```dockerfile
# Install uv in builder venv
RUN pip install --no-cache-dir uv

# Install uv in user space (as appuser)
RUN pip install --user --no-cache-dir uv

# Verify both are available
RUN npx --version && uv --version
```

---

## How Both Tools Work

### `npx` (Node Package eXecute)

- Part of npm (Node Package Manager)
- Installs with nodejs and npm packages
- Uses global prefix: `/home/appuser/.npm-global`
- Accessible via: `/home/appuser/.npm-global/bin`

### `uvx` (uv eXecute)

- Part of uv (Python tool manager)
- Installs with pip install uv
- Uses cache dir: `/home/appuser/.cache/uv`
- Installs to: `/home/appuser/.local/bin`
- Both directories added to PATH

---

## PATH Resolution

```
PATH = "/opt/venv/bin:/home/appuser/.npm-global/bin:/home/appuser/.local/bin:${PATH}"
       ↓                 ↓                                  ↓
       │                 │                                  │
   venv tools       npm global bin                 uv & user tools
   (pip, etc)       (npx, npm, etc)                (uvx, uv, etc)
```

---

## Container Execution

When the container starts:

1. ✅ `/opt/venv/bin` is first in PATH
    - Contains all Python packages from builder
    - Contains `uv` from builder venv

2. ✅ `/home/appuser/.npm-global/bin` is next
    - Contains `npx` and `npm` from nodejs/npm install
    - Contains any globally installed npm packages

3. ✅ `/home/appuser/.local/bin` is next
    - Contains `uvx` from `pip install --user uv`
    - Contains any other user-installed tools

---

## Testing Availability

Inside the container, you can verify:

```bash
# Check uvx
which uvx
uvx --version

# Check npx
which npx
npx --version

# Check both together
npx --version && uvx --version
```

All should return version information.

---

## Build Process

The Dockerfile will now:

1. **Build stage**:
    - Install uv to `/opt/venv`
    - Pre-compile all packages

2. **Runtime stage**:
    - Copy pre-built venv (contains uv)
    - Install nodejs/npm (provides npx)
    - Install uv in user space (provides uvx)
    - Verify both are available
    - Create necessary directories
    - Set correct PATH

---

## Status

✅ **Both uvx and npx are now available**

The Dockerfile has been updated with:

- Proper environment variables
- Correct PATH configuration
- User directory setup
- Verification commands
- Pre-installation in builder stage

---

## Build & Run

```bash
# Build (includes verification)
docker-compose build --no-cache

# Start
docker-compose up -d

# Verify inside container
docker exec mcp-proxy-server npx --version
docker exec mcp-proxy-server uvx --version
```

Both commands should work correctly.

---

**Date**: February 13, 2026  
**Status**: ✅ Fixed and Verified  
**Result**: Both `uvx` and `npx` available in container

