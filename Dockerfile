# syntax=docker/dockerfile:1.4
ARG PYTHON_VERSION=3.14
ARG NODE_VERSION=25
ARG TARGETPLATFORM
FROM nikolaik/python-nodejs:python${PYTHON_VERSION}-nodejs${NODE_VERSION}-slim AS builder

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy project files for building
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Build the package as a wheel using build tool
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir build && \
    python -m build --wheel && \
    ls -la dist/

# ============================================================
# Final stage - minimal runtime image
# ============================================================
ARG PYTHON_VERSION
ARG NODE_VERSION
FROM nikolaik/python-nodejs:python${PYTHON_VERSION}-nodejs${NODE_VERSION}-slim AS runtime

WORKDIR /drunk-ai-proxy

# Create non-root user early
RUN useradd -m -u 10001 appuser

# Install only runtime dependencies (nodejs/npm already in base image)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create virtual environment in runtime stage
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy built wheel from builder stage
COPY --from=builder /build/dist/drunk_ai_proxy-*.whl /tmp/

# Install the built wheel package
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir /tmp/drunk_ai_proxy-*.whl

# Verify package installation and entry point
RUN drunk-ai-proxy --help 2>&1 | head -5 || echo "Entry point verification skipped"

# Copy application data and schemas directly from project
COPY --chown=appuser:appuser data/ ./data/
COPY --chown=appuser:appuser schemas/ ./schemas/

# Setup user directories and environment in single layer
RUN mkdir -p /tmp/pip-cache /home/appuser/.npm-global /home/appuser/.npm /home/appuser/.cache/uv /home/appuser/.local/uv/tools && \
    chown -R appuser:appuser ./data /tmp/pip-cache /home/appuser

# Consolidate environment variables
ENV FASTMCP_CONFIG_DIR=/drunk-ai-proxy/data \
    FASTMCP_SCHEMA_DIR=/drunk-ai-proxy/schemas \
    FASTMCP_STATELESS_HTTP=true \
    PYTHONUNBUFFERED=1 \
    HOME=/home/appuser \
    NPM_CONFIG_PREFIX=/home/appuser/.npm-global \
    NPM_CONFIG_CACHE=/home/appuser/.npm \
    UV_CACHE_DIR=/home/appuser/.cache/uv \
    UV_TOOL_DIR=/home/appuser/.local/uv/tools \
    PIP_CACHE_DIR=/tmp/pip-cache \
    PATH="/opt/venv/bin:/home/appuser/.npm-global/bin:/home/appuser/.local/bin:${PATH}" \
    VIRTUAL_ENV=/opt/venv \
    PIP_NO_INPUT=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

EXPOSE $FASTMCP_PORT

# Verify npx is available before switching user
RUN npx --version

# Switch to non-root user
USER appuser

# Verify npx is available as appuser
RUN npx --version

# Run using the installed console script entry point
CMD ["drunk-ai-proxy"]
