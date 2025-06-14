#!/bin/bash
set -e

echo "Installing MLflow dependencies..."
apt-get update && apt-get install -y curl
pip install mlflow boto3 psycopg2-binary

echo "Starting MLflow server..."
# Set the gunicorn command args environment variable
export GUNICORN_CMD_ARGS="--bind 0.0.0.0:5000 --timeout 120"

# Start MLflow server
exec mlflow server \
    --backend-store-uri postgresql://mlops:mlops123@postgres:5432/mlops \
    --default-artifact-root s3://mlflow-artifacts/ \
    --host 0.0.0.0 \
    --port 5000 \
    --serve-artifacts \
    --workers 2