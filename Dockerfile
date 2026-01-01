FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    libx11-dev \
    libxrandr-dev \
    libxinerama-dev \
    libxcursor-dev \
    libxi-dev \
    scrot \
    xdotool \
    docker.io \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install uv
RUN pip install uv

# Copy project configuration and lock file
COPY pyproject.toml uv.lock ./

# Install Python dependencies using uv sync for reproducible builds
RUN uv pip sync --system --no-cache uv.lock

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p /var/lib/watchman/shots /var/lib/watchman/ocr /var/lib/watchman/chunks

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default command (overridden by docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
