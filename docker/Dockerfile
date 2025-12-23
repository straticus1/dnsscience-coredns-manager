# DNS Science Toolkit - Multi-stage Docker Build
# Supports API, CLI, MCP Server, and Admin Panel

FROM python:3.12-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    dnsutils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ==============================================================================
# Builder stage - install dependencies
# ==============================================================================
FROM base as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy pyproject.toml first for caching
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install -e ".[all]"

# ==============================================================================
# Dashboard builder stage - build React dashboard
# ==============================================================================
FROM node:20-slim as dashboard-builder

WORKDIR /app/dashboard

# Copy dashboard source
COPY src/dnsscience/web/dashboard/package*.json ./
RUN npm ci

COPY src/dnsscience/web/dashboard ./
RUN npm run build

# ==============================================================================
# Production image - API Server
# ==============================================================================
FROM base as api

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY src/ ./src/
COPY pyproject.toml ./

# Install the package
RUN pip install -e .

# Copy built dashboard
COPY --from=dashboard-builder /app/dashboard/dist ./src/dnsscience/web/dashboard/dist

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/live || exit 1

# Run API server
CMD ["uvicorn", "dnsscience.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ==============================================================================
# Production image - CLI
# ==============================================================================
FROM base as cli

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY src/ ./src/
COPY pyproject.toml ./

# Install the package
RUN pip install -e .

ENTRYPOINT ["dnsctl"]
CMD ["--help"]

# ==============================================================================
# Production image - MCP Server
# ==============================================================================
FROM base as mcp

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY src/ ./src/
COPY pyproject.toml ./

# Install the package
RUN pip install -e .

# MCP server runs over stdio
CMD ["python", "-m", "dnsscience.mcp.server"]

# ==============================================================================
# Production image - Admin Panel (htmx)
# ==============================================================================
FROM base as admin

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY src/ ./src/
COPY pyproject.toml ./

# Install the package
RUN pip install -e .

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "dnsscience.web.admin.app:app", "--host", "0.0.0.0", "--port", "8001"]

# ==============================================================================
# Production image - Kubernetes Operator
# ==============================================================================
FROM base as operator

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY src/ ./src/
COPY pyproject.toml ./

# Install the package with k8s extras
RUN pip install -e ".[k8s]"

CMD ["python", "-m", "dnsscience.core.k8s.operator"]

# ==============================================================================
# Default production image (API + Dashboard)
# ==============================================================================
FROM api as production
