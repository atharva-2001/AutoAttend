# Start with the Python base image
FROM python:3.12-slim

# Install system dependencies including libgl1 which OpenCV needs
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user with the same UID as your local user
# Replace 1000 with your actual UID (you can find it by running 'id -u' in your terminal)
RUN useradd -m -u 0 appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Install system dependencies including RTSP-related packages
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgstreamer1.0-0 \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .
# Set environment variables for OpenCV
ENV OPENCV_FFMPEG_CAPTURE_OPTIONS="rtsp_transport;udp|timeout;20000000"

# Expose the port
EXPOSE 8000

# Change ownership of the application files
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
