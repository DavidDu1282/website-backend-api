# Use the official Python 3.10 image
FROM python:3.10-slim

# Set environment variables to prevent buffering
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project (excluding files in .dockerignore)
COPY . .

COPY secrets/fortune-telling-website-api-6328be4e7114.json /app/fortune-telling-website-api-6328be4e7114.json

# 🔹 Set Google environment variable inside the container
ENV GOOGLE_APPLICATION_CREDENTIALS="/app/secrets/fortune-telling-website-api-6328be4e7114.json"
ENV GOOGLE_PROJECT_ID="fortune-telling-website-api"
ENV GOOGLE_REGION="us-central1"

# Expose the application port (assume FastAPI runs on 8000)
EXPOSE 8000

# Run the FastAPI application with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
