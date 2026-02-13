FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY main.py .
COPY config.json .

# Create directory for runtime files
RUN mkdir -p /app/data

# Environment variables
ENV MCP_CONFIG_FILE=/app/config.json
ENV MCP_PROXIES_FILE=/app/data/proxies.json

# Expose port (if running HTTP server)
EXPOSE 8000

# Run the application
CMD ["python", "main.py"]
