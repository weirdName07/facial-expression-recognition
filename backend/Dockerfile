# Backend Dockerfile - Optimized for AI & OpenCV
FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# Install system dependencies for OpenCV, Mediapipe, and DeepFace
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download/warmup models if needed (optional optimization)
# RUN python -c "from deepface import DeepFace; DeepFace.build_model('Facenet512')"

# Copy the rest of the backend code
COPY . .

# Expose the API port
EXPOSE 8000

# Start the unified runner
CMD ["python", "run_all_services.py"]
