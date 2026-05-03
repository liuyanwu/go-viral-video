FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV OUTPUT_DIR=/app/output

# Copy dependency file first for better layer caching
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir .

# Copy the rest of the project files
COPY . .

# Create output directory
RUN mkdir -p /app/output

# Add non-root user
RUN groupadd -r appuser && useradd -r -g appuser -m appuser
USER appuser

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)" || exit 1

# Default entrypoint
ENTRYPOINT ["python", "main.py"]
CMD ["--help"]
