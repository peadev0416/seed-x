# Use the official Python base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application code including frontend
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Run using uvicorn and rely on python-dotenv to load .env
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
