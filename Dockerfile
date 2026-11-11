# Start from a small official Python image: less to download, less to patch, faster builds.
FROM python:3.12-slim

# Work in /app so every later path is relative to one known folder.
WORKDIR /app

# Copy only requirements.txt first. Docker caches this layer, so rebuilds skip the install unless dependencies change.
COPY requirements.txt .

# Install the pinned dependencies. --no-cache-dir keeps pip's download cache out of the image.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app code last, because it changes most often.
COPY main.py .

# Document the port the app listens on (Cloud Run ignores this and uses $PORT).
EXPOSE 8080

# Cloud Run tells the container which port to use through $PORT; default to 8080 for local runs.
# The shell form lets $PORT expand, and exec makes uvicorn receive shutdown signals directly.
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
