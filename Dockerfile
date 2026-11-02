# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Set environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    MCP_TRANSPORT=stdio

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy project definition and install dependencies
COPY pyproject.toml README.md ./
RUN uv pip install --system --no-cache -r pyproject.toml

# Copy source code
COPY src/ ./src/

# Install the package itself
RUN uv pip install --system --no-cache --no-deps -e .

# Create non-root user
RUN useradd -m -u 1000 mcpuser && chown -R mcpuser:mcpuser /app
USER mcpuser

EXPOSE 8000

# Default entrypoint runs the MCP server
ENTRYPOINT ["okta-mcp-server"]
