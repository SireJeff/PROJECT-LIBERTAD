# Use a lightweight and secure base image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the dependency file first to leverage Docker's layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# --- NEW: Copy all configuration and source code ---
# This will copy main.py, .env, and emails.txt into the image.
# The .dockerignore file will prevent other things from being copied.
COPY . .

# Set the persistent storage path (the container still needs a place for the session)
ENV PERSISTENT_STORAGE_PATH=/app/data

# Command to run the application
CMD ["python", "main.py"]