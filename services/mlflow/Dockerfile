FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    mlflow \
    boto3 \
    psycopg2-binary \
    psutil \
    nvidia-ml-py \
    gpustat \
    matplotlib \
    seaborn \
    plotly

# Create a custom gunicorn config
RUN echo "bind = '0.0.0.0:5000'" > /gunicorn.conf.py

# Set environment variables
ENV GUNICORN_CMD_ARGS="--config /gunicorn.conf.py"

# Expose port
EXPOSE 5000

# Set environment variables for system metrics
ENV MLFLOW_ENABLE_SYSTEM_METRICS_LOGGING=true
ENV MLFLOW_SYSTEM_METRICS_SAMPLING_INTERVAL=10
ENV MLFLOW_SYSTEM_METRICS_SAMPLES_BEFORE_LOGGING=1

# Run MLflow server
CMD mlflow server \
    --backend-store-uri ${MLFLOW_BACKEND_STORE_URI} \
    --default-artifact-root ${MLFLOW_DEFAULT_ARTIFACT_ROOT} \
    --host 0.0.0.0 \
    --port 5000 \
    --serve-artifacts