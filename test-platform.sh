#!/bin/bash

# Test script for platform services

echo "Testing MLOps Platform Services Integration"
echo "=========================================="

# Check if infrastructure is running
echo "1. Checking infrastructure services..."
docker ps | grep mlops-platform | grep -E "postgres|redis|minio" || {
    echo "Infrastructure not running. Starting..."
    cd mlops-platform
    docker compose -f docker-compose.platform.yml up -d postgres redis minio
    sleep 10
}

# Test connectivity
echo -e "\n2. Testing connectivity..."
echo -n "PostgreSQL: "
docker exec mlops-platform-postgres-1 pg_isready -U mlops && echo "✅ Connected" || echo "❌ Failed"

echo -n "Redis: "
docker exec mlops-platform-redis-1 redis-cli ping | grep -q PONG && echo "✅ Connected" || echo "❌ Failed"

echo -n "MinIO: "
curl -s http://localhost:9000/minio/health/live | grep -q "ok" && echo "✅ Connected" || echo "❌ Failed"

# Test healthcare app integration
echo -e "\n3. Testing Healthcare App Integration..."
echo -n "Healthcare Service: "
curl -s http://localhost:8092/health | grep -q "healthy" && echo "✅ Running" || echo "❌ Not running"

echo -n "Redis Integration: "
curl -s http://localhost:8092/stats | jq -r '.redis_connected' | grep -q true && echo "✅ Connected to platform Redis" || echo "❌ Not connected"

# Test a healthcare query
echo -e "\n4. Testing Healthcare Query..."
response=$(curl -s -X POST http://localhost:8092/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are some balance exercises?"}')

method=$(echo $response | jq -r '.method')
category=$(echo $response | jq -r '.category')

echo "Method: $method"
echo "Category: $category"

if [[ "$method" == "ml_model" && "$category" == "adl_mobility" ]]; then
    echo "✅ Healthcare AI working correctly with reorganized structure"
else
    echo "❌ Healthcare AI response incorrect"
fi

echo -e "\n=========================================="
echo "Platform Integration Test Complete"