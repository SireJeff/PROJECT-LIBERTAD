# Use a lightweight and secure base image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the dependency file first to leverage Docker's layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY . .

# Create the default directory for persistent storage
# This directory will be the target for a volume mount
RUN mkdir -p /app/data

# Set environment variables (can be overridden at runtime)
# We define PERSISTENT_STORAGE_PATH here to ensure it points to the created directory
ENV PYTHONUNBUFFERED=1 \
    PERSISTENT_STORAGE_PATH=/app/data

# Command to run the application
CMD ["python", "main.py"]