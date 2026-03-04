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

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy project metadata only (before source code, for better cache invalidation)
COPY pyproject.toml ./

# Copy application source code (needed before pip install)
COPY src/ ./src/

# Install runtime dependencies with BuildKit persistent cache
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir . && \
    pip install --no-cache-dir uv

# ============================================================
# Final stage - minimal runtime image
# ============================================================
ARG PYTHON_VERSION
ARG NODE_VERSION
FROM nikolaik/python-nodejs:python${PYTHON_VERSION}-nodejs${NODE_VERSION}-slim AS runtime

WORKDIR /drunk-proxy

# Create non-root user early
RUN useradd -m -u 10001 appuser

# Install only runtime dependencies (nodejs/npm already in base image)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


# Copy pre-built virtual environment from builder
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv

# Activate venv
ENV PATH="/opt/venv/bin:$PATH" \
    VIRTUAL_ENV="/opt/venv" \
    PIP_NO_INPUT=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Copy application code
COPY --chown=appuser:appuser src/ ./
COPY --chown=appuser:appuser schemas/ ./schemas/

# Create data directory and setup user directories in single layer
RUN mkdir -p ./data /tmp/pip-cache /home/appuser/.npm-global /home/appuser/.npm /home/appuser/.cache/uv /home/appuser/.local/uv/tools && \
    chown -R appuser:appuser ./data /tmp/pip-cache /home/appuser

# Consolidate environment variables
ENV FASTMCP_CONFIG_DIR=/drunk-proxy/data \
    FASTMCP_SCHEMA_DIR=/drunk-proxy/schemas \
    FASTMCP_STATELESS_HTTP=true \
    PYTHONPATH=/drunk-proxy \
    PYTHONUNBUFFERED=1 \
    HOME=/home/appuser \
    NPM_CONFIG_PREFIX=/home/appuser/.npm-global \
    NPM_CONFIG_CACHE=/home/appuser/.npm \
    UV_CACHE_DIR=/home/appuser/.cache/uv \
    UV_TOOL_DIR=/home/appuser/.local/uv/tools \
    PIP_CACHE_DIR=/tmp/pip-cache \
    PATH="/opt/venv/bin:/home/appuser/.npm-global/bin:/home/appuser/.local/bin:${PATH}"

EXPOSE $FASTMCP_PORT

# Verify npx is available before switching user
RUN npx --version

# Switch to non-root user
USER appuser

# Verify both npx and uvx are available (uv already in venv from builder)
RUN npx --version && uvx --version

CMD ["python", "-m", "main"]
