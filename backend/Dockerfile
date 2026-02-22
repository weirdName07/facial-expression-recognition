# Backend Dockerfile - Optimized for AI & OpenCV
FROM python:3.12-slim-bookworm

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Set PYTHONPATH to root so we can 'import backend...'
ENV PYTHONPATH=/app

WORKDIR /app

# Install system dependencies for OpenCV, Mediapipe, and DeepFace
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code into a subdirectory named 'backend'
# This ensures that 'import backend.xxx' works as expected
COPY . ./backend

# Expose the API port
EXPOSE 8000

# Start the unified runner using the module path
CMD ["python", "backend/run_all_services.py"]
