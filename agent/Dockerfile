# WildWatch Detection Agent
# Multi-stage build for smaller final image

FROM python:3.11-slim AS base

# Install system dependencies (ffmpeg + deno for yt-dlp JS runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install deno (required by latest yt-dlp for YouTube JS player parsing)
RUN curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/usr/local sh

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py .

# Create frames directory
RUN mkdir -p /app/frames

# Environment defaults (override via docker-compose or -e)
ENV FRAME_INTERVAL_SECONDS=60
ENV MAX_CONCURRENT_EXTRACTIONS=4
ENV BATCH_SIZE=5
ENV FRAME_QUALITY=85
ENV FRAME_MAX_DIMENSION=1280
ENV OFFLINE_RETRY_INTERVAL=300
ENV SPECIESNET_CONFIDENCE_THRESHOLD=0.15
ENV SPECIESNET_CLASSIFICATION_THRESHOLD=0.5

# Model cache directory — persisted via volume
ENV TORCH_HOME=/app/.cache/torch
ENV HF_HOME=/app/.cache/huggingface

CMD ["python", "main.py"]
