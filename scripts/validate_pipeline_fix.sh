#!/bin/bash

# Validate that CI/CD pipeline fixes are working
# This script checks for common issues that would break the pipeline

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🔍 Validating CI/CD Pipeline Fixes"
echo "=================================="

# Check if required files exist
echo ""
echo "📁 Checking required files..."

required_files=(
    "models/healthcare-ai/requirements.txt"
    "models/healthcare-ai/service.py"
    "models/healthcare-ai/Dockerfile"
    "services/ab-testing/requirements.txt"
    "services/ab-testing/src/main.py"
    "services/ab-testing/Dockerfile"
    "services/mlflow/Dockerfile"
    "deployment/k8s/environments/staging/namespace.yaml"
    "deployment/k8s/environments/production/namespace.yaml"
    "tests/unit/"
    "tests/integration/"
    "tests/e2e/"
)

for file in "${required_files[@]}"; do
    if [ -e "$file" ]; then
        echo -e "${GREEN}✅ $file${NC}"
    else
        echo -e "${RED}❌ $file${NC}"
        exit 1
    fi
done

# Check Python syntax
echo ""
echo "🐍 Checking Python syntax..."

python_files=(
    "models/healthcare-ai/service.py"
    "services/ab-testing/src/main.py"
    "services/ab-testing/src/models.py"
    "services/ab-testing/src/statistics.py"
    "services/ab-testing/src/safety_monitor.py"
    "services/ab-testing/src/metrics.py"
)

for file in "${python_files[@]}"; do
    if python3 -m py_compile "$file" 2>/dev/null; then
        echo -e "${GREEN}✅ $file syntax OK${NC}"
    else
        echo -e "${RED}❌ $file syntax error${NC}"
        exit 1
    fi
done

# Check Docker files
echo ""
echo "🐳 Checking Dockerfiles..."

dockerfiles=(
    "models/healthcare-ai/Dockerfile"
    "services/ab-testing/Dockerfile"
    "services/mlflow/Dockerfile"
)

for dockerfile in "${dockerfiles[@]}"; do
    if [ -f "$dockerfile" ]; then
        if grep -q "FROM" "$dockerfile" && grep -q "CMD\|ENTRYPOINT" "$dockerfile"; then
            echo -e "${GREEN}✅ $dockerfile structure OK${NC}"
        else
            echo -e "${RED}❌ $dockerfile missing FROM or CMD/ENTRYPOINT${NC}"
            exit 1
        fi
    else
        echo -e "${RED}❌ $dockerfile not found${NC}"
        exit 1
    fi
done

# Check Kubernetes manifests
echo ""
echo "☸️ Checking Kubernetes manifests..."

k8s_dirs=(
    "deployment/k8s/environments/dev"
    "deployment/k8s/environments/staging"
    "deployment/k8s/environments/production"
)

for dir in "${k8s_dirs[@]}"; do
    if [ -d "$dir" ]; then
        yaml_count=$(find "$dir" -name "*.yaml" | wc -l)
        if [ "$yaml_count" -gt 0 ]; then
            echo -e "${GREEN}✅ $dir ($yaml_count YAML files)${NC}"
        else
            echo -e "${RED}❌ $dir has no YAML files${NC}"
            exit 1
        fi
    else
        echo -e "${RED}❌ $dir not found${NC}"
        exit 1
    fi
done

# Check GitHub Actions workflow
echo ""
echo "🔄 Checking GitHub Actions workflow..."

workflow_file=".github/workflows/ci-cd.yml"
if [ -f "$workflow_file" ]; then
    # Check for key sections
    if grep -q "healthcare-ai" "$workflow_file" && \
       grep -q "ab-testing" "$workflow_file" && \
       grep -q "mlflow" "$workflow_file"; then
        echo -e "${GREEN}✅ CI/CD workflow includes all services${NC}"
    else
        echo -e "${RED}❌ CI/CD workflow missing service references${NC}"
        exit 1
    fi
    
    # Check for updated paths
    if grep -q "models/healthcare-ai" "$workflow_file" && \
       grep -q "services/ab-testing" "$workflow_file"; then
        echo -e "${GREEN}✅ CI/CD workflow has updated paths${NC}"
    else
        echo -e "${RED}❌ CI/CD workflow has outdated paths${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ $workflow_file not found${NC}"
    exit 1
fi

# Check requirements files
echo ""
echo "📦 Checking requirements files..."

req_files=(
    "models/healthcare-ai/requirements.txt"
    "services/ab-testing/requirements.txt"
)

for req_file in "${req_files[@]}"; do
    if [ -f "$req_file" ]; then
        line_count=$(wc -l < "$req_file")
        if [ "$line_count" -gt 0 ]; then
            echo -e "${GREEN}✅ $req_file ($line_count dependencies)${NC}"
        else
            echo -e "${YELLOW}⚠️ $req_file is empty${NC}"
        fi
    else
        echo -e "${RED}❌ $req_file not found${NC}"
        exit 1
    fi
done

# Check test structure
echo ""
echo "🧪 Checking test structure..."

test_dirs=(
    "tests/unit"
    "tests/integration" 
    "tests/e2e"
)

for test_dir in "${test_dirs[@]}"; do
    if [ -d "$test_dir" ]; then
        test_count=$(find "$test_dir" -name "test_*.py" | wc -l)
        echo -e "${GREEN}✅ $test_dir ($test_count test files)${NC}"
    else
        echo -e "${RED}❌ $test_dir not found${NC}"
        exit 1
    fi
done

echo ""
echo -e "${GREEN}🎉 All CI/CD pipeline validation checks passed!${NC}"
echo ""
echo "💡 Next steps:"
echo "1. Run 'git add . && git commit -m \"Fix CI/CD pipeline for new architecture\"'"
echo "2. Push to GitHub to trigger the pipeline"
echo "3. Monitor the GitHub Actions tab for successful execution"
echo ""
echo "🚀 Pipeline should now work with:"
echo "- Updated service paths"
echo "- A/B testing service integration"
echo "- New Kubernetes deployment structure" 
echo "- Multi-service Docker builds"
echo "- Enhanced security scanning"