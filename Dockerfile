# MACS - Multi-Agent Collaboration System
# Multi-stage build for smaller production image

# ============================================
# Stage 1: Builder
# ============================================
FROM python:3.10-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ============================================
# Stage 2: Production
# ============================================
FROM python:3.10-slim as production

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r macs && useradd -r -g macs macs

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /home/macs/.local

# Copy application code
COPY --chown=macs:macs macs_pkg/ ./macs_pkg/
COPY --chown=macs:macs examples/ ./examples/
COPY --chown=macs:macs README.md .
COPY --chown=macs:macs LICENSE .

# Set environment variables
ENV PATH=/home/macs/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV MACS_LOG_LEVEL=INFO

# Switch to non-root user
USER macs

# Default command
CMD ["python", "-c", "from macs_pkg.llm import MiniMaxProvider; print('MACS ready!')"]

# ============================================
# Stage 3: Development
# ============================================
FROM production as development

# Install development dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Install pytest and dev tools
RUN pip install --no-cache-dir --user pytest pytest-asyncio pytest-cov

# Mount source for hot reload (use docker-compose for volumes)
WORKDIR /app
