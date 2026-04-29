# MACS - Multi-Agent Collaboration System
# Dockerfile for containerized deployment

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml ./
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install optional dependencies for full features
RUN pip install --no-cache-dir \
    sentence-transformers \
    chromadb \
    faiss-cpu \
    redis \
    prometheus-client \
    fastapi \
    uvicorn

# Copy application code
COPY macs_pkg/ ./macs_pkg/
COPY examples/ ./examples/

# Set Python path
ENV PYTHONPATH=/app

# Expose port for API server
EXPOSE 8000

# Default command - run the API server
CMD ["python", "-m", "macs_pkg.api.server"]
