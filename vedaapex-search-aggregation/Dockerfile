FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable buffered stdout logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /workspace

# Install system dependencies (FFmpeg, FFprobe, and OpenCV runtime libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    curl \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY . .

# Expose FastAPI web port
ENV PORT=8000
EXPOSE 8000

# Default entrypoint starts the FastAPI server
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
