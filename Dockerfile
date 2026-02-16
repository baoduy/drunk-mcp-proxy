ARG TARGETPLATFORM
FROM --platform=$TARGETPLATFORM python:3.14-slim as builder

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy project metadata and install runtime deps into venv
COPY pyproject.toml ./
COPY src/ ./src/

RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir .

# Install uv and related tools in venv
RUN pip install --no-cache-dir uv

# ============================================================
# Final stage - minimal runtime image
# ============================================================
FROM --platform=$TARGETPLATFORM python:3.14-slim

WORKDIR /app

# Create non-root user early
RUN useradd -m -u 10001 appuser

# Install only runtime dependencies (no build tools)
# Include nodejs for npx availability
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      nodejs \
      npm \
      curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy pre-built virtual environment from builder
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv
COPY schemas/ ./app/schemas/

# Activate venv
ENV PATH="/opt/venv/bin:$PATH" \
    VIRTUAL_ENV="/opt/venv" \
    PIP_NO_INPUT=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Copy application code
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser schemas/ ./schemas/

# Create data directory
RUN mkdir -p /app/data && chown appuser:appuser /app/data

# Create pip cache directory for runtime installations
RUN mkdir -p /tmp/pip-cache && chown appuser:appuser /tmp/pip-cache

# Consolidate environment variables
ENV FASTMCP_CONFIG_DIR=/app/data \
    FASTMCP_SCHEMA_DIR=/app/schemas \
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

# Setup user directories
RUN mkdir -p /home/appuser/.npm-global \
             /home/appuser/.npm \
             /home/appuser/.cache/uv \
             /home/appuser/.local/uv/tools && \
    chown -R appuser:appuser /home/appuser

EXPOSE $FASTMCP_PORT

# Verify npx is available before switching user
RUN npx --version

# Switch to non-root user
USER appuser

# Verify both npx and uvx are available (uv already in venv from builder)
RUN npx --version && uvx --version

CMD ["python", "-m", "src.main"]
