# Dockerfile to run the backend in a reproducible container
FROM python:3.11-slim
WORKDIR /app

# System build deps for native wheels
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (better layer caching)
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy application code
COPY backend/ /app/backend/

WORKDIR /app/backend

# Train ML model if not present (uses synthetic data)
RUN python -m app.ml.train_model --output-dir app/ml/models || \
    echo "Warning: ML model training skipped (non-critical)"

# Expose API port
EXPOSE 8000

# Default: run the API server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
