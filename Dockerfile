# =============================================================================
# Stage 1: Build stage (install dependencies)
# =============================================================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# =============================================================================
# Stage 2: Runtime stage (minimal image)
# =============================================================================
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /root/.local /root/.local

# Add Python user site-packages to PATH
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY src/ src/
COPY skills/ skills/

# Create memory directory (will be overridden by volume in Cloud Run)
RUN mkdir -p /app/data/memory

# Set environment variables for Cloud Run
ENV PYTHONUNBUFFERED=1 \
    PORT=8080

# Health check (Cloud Run uses this for readiness/liveness)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health').read()"

# Expose port (Cloud Run injects PORT env var)
EXPOSE 8080

# Run application
CMD ["python", "-m", "src.main"]
