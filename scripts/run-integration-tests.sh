#!/bin/bash

# MLOps Platform Local Integration Test Runner
# This script replicates the CI integration test workflow locally

set -e

echo "🚀 Starting MLOps Platform Local Integration Tests"
echo "============================================================"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to cleanup on exit
cleanup() {
    print_status "Cleaning up containers..."
    docker compose -f docker-compose.platform.yml down -v || true
}

# Set trap to cleanup on script exit
trap cleanup EXIT

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Create test environment file
# NOTE: These are test-only credentials used for local integration testing
# In production, these values should come from secure secret management
print_status "Creating test environment configuration..."
cat > .env << EOF
POSTGRES_PASSWORD=test123  # TEST ONLY - Use environment variables in production
MINIO_ROOT_PASSWORD=test123  # TEST ONLY - Use environment variables in production
GRAFANA_ADMIN_PASSWORD=test123  # TEST ONLY - Use environment variables in production
EOF

# Cleanup any existing containers
print_status "Stopping any existing containers..."
docker compose -f docker-compose.platform.yml down -v || true

# Try to pull latest images first
print_status "Pulling latest images..."
docker compose -f docker-compose.platform.yml pull --ignore-pull-failures || print_warning "Some images could not be pulled, will try to build"

# Start MLOps Platform services
print_status "Starting MLOps Platform services..."
docker compose -f docker-compose.platform.yml up -d --build

print_status "Waiting for services to initialize (120 seconds)..."
sleep 120

# Check infrastructure services first
print_status "Checking infrastructure services..."

echo "  Checking PostgreSQL..."
# Using test password from .env file created above
timeout 300 bash -c 'until PGPASSWORD=test123 pg_isready -h localhost -U mlops -d mlops_platform > /dev/null 2>&1; do sleep 5; done' || {
    print_error "PostgreSQL failed to start"
    docker compose -f docker-compose.platform.yml logs postgres
    exit 1
}
print_success "PostgreSQL is ready"

echo "  Checking Redis..."
timeout 300 bash -c 'until docker compose -f docker-compose.platform.yml exec -T redis redis-cli ping > /dev/null 2>&1; do sleep 5; done' || {
    print_error "Redis failed to start"
    docker compose -f docker-compose.platform.yml logs redis
    exit 1
}
print_success "Redis is ready"

echo "  Checking MinIO..."
timeout 300 bash -c 'until curl -f http://localhost:9000/minio/health/live > /dev/null 2>&1; do sleep 5; done' || {
    print_error "MinIO failed to start"
    docker compose -f docker-compose.platform.yml logs minio
    exit 1
}
print_success "MinIO is ready"

print_success "All infrastructure services are healthy!"

# Check application services
print_status "Checking application services..."

echo "  Checking Model Registry (port 8000)..."
timeout 300 bash -c 'until curl -f http://localhost:8000/health > /dev/null 2>&1; do sleep 5; done' || {
    print_error "Model Registry failed to start"
    docker compose -f docker-compose.platform.yml logs model-registry
    exit 1
}
print_success "Model Registry is healthy"

echo "  Checking Experiment Tracking (port 8003)..."
timeout 300 bash -c 'until curl -f http://localhost:8003/health > /dev/null 2>&1; do sleep 5; done' || {
    print_error "Experiment Tracking failed to start"
    docker compose -f docker-compose.platform.yml logs experiment-tracking
    exit 1
}
print_success "Experiment Tracking is healthy"

echo "  Checking Feature Store (port 8002)..."
timeout 300 bash -c 'until curl -f http://localhost:8002/health > /dev/null 2>&1; do sleep 5; done' || {
    print_error "Feature Store failed to start"
    docker compose -f docker-compose.platform.yml logs feature-store
    exit 1
}
print_success "Feature Store is healthy"

echo "  Checking Pipeline Orchestrator (port 8004)..."
timeout 300 bash -c 'until curl -f http://localhost:8004/health > /dev/null 2>&1; do sleep 5; done' || {
    print_error "Pipeline Orchestrator failed to start"
    docker compose -f docker-compose.platform.yml logs pipeline-orchestrator
    exit 1
}
print_success "Pipeline Orchestrator is healthy"

echo "  Checking A/B Testing (port 8090)..."
timeout 300 bash -c 'until curl -f http://localhost:8090/health > /dev/null 2>&1; do sleep 5; done' || {
    print_error "A/B Testing failed to start"
    docker compose -f docker-compose.platform.yml logs ab-testing
    exit 1
}
print_success "A/B Testing is healthy"

print_success "All application services are healthy!"

# Run integration tests
print_status "Running integration tests..."

echo "  Testing Model Registry API..."
response=$(curl -s -X POST http://localhost:8000/api/models \
    -H "Content-Type: application/json" \
    -d '{"name": "test-model", "version": "1.0.0", "framework": "test"}' || echo "FAILED")
if [[ "$response" == "FAILED" ]]; then
    print_error "Model Registry API test failed"
    exit 1
fi
print_success "Model Registry API test passed"

echo "  Testing Experiment Tracking API..."
response=$(curl -s -X POST http://localhost:8003/api/experiments \
    -H "Content-Type: application/json" \
    -d '{"name": "test-experiment", "description": "Integration test"}' || echo "FAILED")
if [[ "$response" == "FAILED" ]]; then
    print_error "Experiment Tracking API test failed"
    exit 1
fi
print_success "Experiment Tracking API test passed"

echo "  Testing Feature Store API..."
response=$(curl -s -X POST http://localhost:8002/api/feature-sets \
    -H "Content-Type: application/json" \
    -d '{"name": "test-features", "description": "Test feature set"}' || echo "FAILED")
if [[ "$response" == "FAILED" ]]; then
    print_error "Feature Store API test failed"
    exit 1
fi
print_success "Feature Store API test passed"

# Check monitoring endpoints
print_status "Checking monitoring endpoints..."

echo "  Checking Prometheus..."
if ! curl -f http://localhost:9090/-/healthy > /dev/null 2>&1; then
    print_error "Prometheus health check failed"
    exit 1
fi
print_success "Prometheus is healthy"

echo "  Checking Grafana..."
if ! curl -f http://localhost:3000/api/health > /dev/null 2>&1; then
    print_error "Grafana health check failed"
    exit 1
fi
print_success "Grafana is healthy"

# Show service status
print_status "Final service status:"
docker compose -f docker-compose.platform.yml ps

print_success "🎉 ALL INTEGRATION TESTS PASSED!"
print_status "Services are running and ready for development."
print_status "Use 'docker compose -f docker-compose.platform.yml down' to stop services."

echo "============================================================"
echo "✅ Local integration test completed successfully"