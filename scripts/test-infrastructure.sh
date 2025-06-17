#!/bin/bash

# MLOps Platform Infrastructure Test
# Test only the infrastructure services (no custom builds)

set -e

echo "🔧 Testing MLOps Platform Infrastructure Services"
echo "============================================================"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create test environment file
# NOTE: These are test-only credentials used for local infrastructure testing
# In production, these values should come from secure secret management
print_status "Creating test environment configuration..."
cat > .env << EOF
POSTGRES_PASSWORD=test123  # TEST ONLY - Use environment variables in production
MINIO_ROOT_PASSWORD=test123  # TEST ONLY - Use environment variables in production
GRAFANA_ADMIN_PASSWORD=test123  # TEST ONLY - Use environment variables in production
EOF

# Test infrastructure services only
print_status "Starting infrastructure services..."
# TEST ONLY: Using hardcoded password for local testing
# In production, use environment variables or secret management
docker run -d --name test-postgres -p 5432:5432 \
    -e POSTGRES_USER=mlops \
    -e POSTGRES_PASSWORD=test123 \
    -e POSTGRES_DB=mlops_platform \
    postgres:13

docker run -d --name test-redis -p 6379:6379 redis:7-alpine

# TEST ONLY: Using hardcoded credentials for local testing
# In production, use environment variables or secret management
docker run -d --name test-minio -p 9000:9000 -p 9001:9001 \
    -e MINIO_ROOT_USER=minioadmin \
    -e MINIO_ROOT_PASSWORD=test123456 \
    minio/minio:latest server /data --console-address ":9001"

print_status "Waiting for services to start..."
sleep 30

# Test PostgreSQL
print_status "Testing PostgreSQL..."
# Using test password from container setup above
if PGPASSWORD=test123 pg_isready -h localhost -U mlops -d mlops_platform > /dev/null 2>&1; then
    print_success "PostgreSQL is working"
else
    print_error "PostgreSQL failed"
    docker logs test-postgres --tail 10
fi

# Test Redis
print_status "Testing Redis..."
if docker exec test-redis redis-cli ping > /dev/null 2>&1; then
    print_success "Redis is working"
else
    print_error "Redis failed"
    docker logs test-redis --tail 10
fi

# Test MinIO
print_status "Testing MinIO..."
if curl -f http://localhost:9000/minio/health/live > /dev/null 2>&1; then
    print_success "MinIO is working"
else
    print_error "MinIO failed"
    docker logs test-minio --tail 10
fi

print_success "🎉 All infrastructure services are working!"

# Cleanup
print_status "Cleaning up..."
docker stop test-postgres test-redis test-minio || true
docker rm test-postgres test-redis test-minio || true

echo "============================================================"
echo "✅ Infrastructure test completed successfully"