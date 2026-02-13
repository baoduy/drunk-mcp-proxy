FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Create directory for runtime files and copy default config
RUN mkdir -p /app/data
COPY mcp.json /app/data/mcp.json

# Environment variables
ENV MCP_CONFIG_FILE=/app/data/mcp.json
ENV MCP_PROXIES_FILE=/app/data/proxies.json
ENV MCP_AUTH_CONFIG_FILE=/app/data/auth.json
ENV PYTHONPATH=/app/src

# Expose port (if running HTTP server)
EXPOSE 8000

# Run the application
CMD ["python", "src/main.py"]
