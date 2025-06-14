#!/bin/bash
set -e

echo "Installing MLflow and dependencies..."
pip install mlflow boto3 psycopg2-binary

echo "Waiting for PostgreSQL to be ready..."
until pg_isready -h postgres -p 5432 -U mlops; do
  echo "PostgreSQL not ready, waiting..."
  sleep 2
done

echo "Waiting for MinIO to be ready..."
until curl -f http://minio:9000/minio/health/live > /dev/null 2>&1; do
  echo "MinIO not ready, waiting..."
  sleep 2
done

echo "All dependencies ready. Starting MLflow server..."

# Start MLflow with proper configuration
exec mlflow server \
    --backend-store-uri postgresql://mlops:mlops123@postgres:5432/mlops \
    --default-artifact-root s3://mlflow-artifacts/ \
    --host 0.0.0.0 \
    --port 5000 \
    --serve-artifacts \
    --workers 1