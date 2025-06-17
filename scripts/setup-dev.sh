#!/bin/bash

# Cirruslabs MLOps Development Environment Setup
# NOTE: This script uses test-only credentials for local development
# In production, use proper secret management for passwords

set -e

echo "🚀 Setting up Cirruslabs MLOps development environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on macOS or Linux
OS="$(uname -s)"
case "${OS}" in
    Linux*)     MACHINE=Linux;;
    Darwin*)    MACHINE=Mac;;
    *)          MACHINE="UNKNOWN:${OS}";;
esac

print_status "Detected OS: $MACHINE"

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        print_warning "kubectl is not installed. Installing kubectl..."
        install_kubectl
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3 first."
        exit 1
    fi
    
    # Check Node.js (for documentation)
    if ! command -v node &> /dev/null; then
        print_warning "Node.js is not installed. Documentation generation will be limited."
    fi
    
    print_status "Prerequisites check completed ✅"
}

# Install kubectl
install_kubectl() {
    if [[ "$MACHINE" == "Mac" ]]; then
        if command -v brew &> /dev/null; then
            brew install kubectl
        else
            print_error "Homebrew not found. Please install kubectl manually."
            exit 1
        fi
    elif [[ "$MACHINE" == "Linux" ]]; then
        curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
        chmod +x kubectl
        sudo mv kubectl /usr/local/bin/
    fi
}

# Set up Python virtual environment
setup_python_env() {
    print_status "Setting up Python virtual environment..."
    
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
    fi
    
    source .venv/bin/activate
    pip install --upgrade pip
    
    # Install common development dependencies
    pip install -r requirements-dev.txt 2>/dev/null || {
        print_warning "requirements-dev.txt not found. Installing basic dependencies..."
        pip install pytest black flake8 mypy pre-commit
    }
    
    print_status "Python environment setup completed ✅"
}

# Set up pre-commit hooks
setup_pre_commit() {
    print_status "Setting up pre-commit hooks..."
    
    if [ -f ".pre-commit-config.yaml" ]; then
        pre-commit install
        print_status "Pre-commit hooks installed ✅"
    else
        print_warning "No pre-commit configuration found. Skipping..."
    fi
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p {logs,data,artifacts,experiments}
    mkdir -p config/{local,dev,staging,prod}
    
    print_status "Directories created ✅"
}

# Set up local configuration
setup_local_config() {
    print_status "Setting up local configuration..."
    
    # Create local environment file
    if [ ! -f ".env.local" ]; then
        cat > .env.local << EOF
# Local Development Configuration
DEBUG=true
LOG_LEVEL=DEBUG

# Database
DATABASE_URL=postgresql://mlops:mlops123@localhost:5432/mlops

# Redis
REDIS_URL=redis://localhost:6379/0

# MinIO (S3-compatible storage) - TEST ONLY credentials
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY:-minioadmin}  # Use env var or test default
MINIO_SECRET_KEY=${MINIO_SECRET_KEY:-minioadmin123}  # Use env var or test default
MINIO_SECURE=false

# Message Queue
RABBITMQ_URL=amqp://mlops:mlops123@localhost:5672/

# Monitoring
PROMETHEUS_URL=http://localhost:9090
GRAFANA_URL=http://localhost:3000

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
EOF
        print_status "Local environment configuration created ✅"
    else
        print_warning "Local environment file already exists. Skipping..."
    fi
}

# Start local services
start_local_services() {
    print_status "Starting local services with Docker Compose..."
    
    # Build and start services
    docker-compose up -d postgres redis rabbitmq minio prometheus grafana
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 10
    
    # Check service health
    check_service_health
}

# Check service health
check_service_health() {
    print_status "Checking service health..."
    
    services=("postgres:5432" "redis:6379" "rabbitmq:15672" "minio:9000" "prometheus:9090" "grafana:3000")
    
    for service in "${services[@]}"; do
        IFS=':' read -r name port <<< "$service"
        if curl -f -s "http://localhost:$port" > /dev/null 2>&1 || nc -z localhost "$port" 2>/dev/null; then
            print_status "$name is healthy ✅"
        else
            print_warning "$name is not responding on port $port"
        fi
    done
}

# Install development tools
install_dev_tools() {
    print_status "Installing development tools..."
    
    # Install common ML/MLOps tools
    if [ -f "requirements-dev.txt" ]; then
        pip install -r requirements-dev.txt
    else
        pip install \
            jupyterlab \
            mlflow \
            kubeflow-pipelines \
            prometheus-client \
            fastapi \
            uvicorn \
            sqlalchemy \
            alembic \
            celery \
            redis \
            boto3 \
            pydantic \
            typer \
            rich
    fi
    
    print_status "Development tools installed ✅"
}

# Generate SSL certificates for local development
generate_ssl_certs() {
    print_status "Generating SSL certificates for local development..."
    
    mkdir -p config/ssl
    
    if [ ! -f "config/ssl/localhost.crt" ]; then
        openssl req -x509 -newkey rsa:4096 -keyout config/ssl/localhost.key -out config/ssl/localhost.crt -days 365 -nodes -subj "/CN=localhost"
        print_status "SSL certificates generated ✅"
    else
        print_warning "SSL certificates already exist. Skipping..."
    fi
}

# Set up documentation
setup_documentation() {
    print_status "Setting up documentation..."
    
    if command -v node &> /dev/null; then
        cd docs
        npm install mkdocs-material
        cd ..
        print_status "Documentation setup completed ✅"
    else
        print_warning "Node.js not found. Skipping documentation setup..."
    fi
}

# Print setup summary
print_summary() {
    echo ""
    echo "🎉 Development environment setup completed!"
    echo ""
    echo "Next steps:"
    echo "1. Activate Python virtual environment: source .venv/bin/activate"
    echo "2. Start all services: make dev-deploy"
    echo "3. Access services:"
    echo "   - API Gateway: http://localhost:8080"
    echo "   - Model Registry: http://localhost:8001"
    echo "   - Grafana: http://localhost:3000 (admin/[check GRAFANA_ADMIN_PASSWORD env var or test default])"
    echo "   - MinIO: http://localhost:9001 ([check MINIO_ACCESS_KEY env var or test default]/[check MINIO_SECRET_KEY env var or test default])"
    echo "   - RabbitMQ: http://localhost:15672 (mlops/mlops123)"
    echo ""
    echo "4. Run tests: make test"
    echo "5. View logs: make logs"
    echo "6. Clean up: make clean"
    echo ""
}

# Main execution
main() {
    check_prerequisites
    setup_python_env
    create_directories
    setup_local_config
    install_dev_tools
    setup_pre_commit
    generate_ssl_certs
    setup_documentation
    start_local_services
    print_summary
}

# Run main function
main "$@"