# MLOps Platform - Enterprise Infrastructure Services

## 🏗️ **Enterprise MLOps Infrastructure**

This repository contains the **reusable MLOps platform** that provides foundational machine learning operations services for enterprise applications. It's designed to be deployed once and used by multiple ML applications across your organization.

## 🎯 **Core Services**

### **🗃️ Model Registry (Port 8000)**
- Universal model versioning and lineage tracking
- Model metadata and artifact management  
- Multi-format model support (pkl, joblib, ONNX, TensorFlow, PyTorch)
- API endpoints for model registration and retrieval

### **🧪 Experiment Tracking (Port 8003)**
- Complete ML experiment management platform
- Hyperparameter tracking and comparison
- Metrics visualization and analysis
- Experiment reproducibility and collaboration

### **🏪 Feature Store (Port 8002)**
- Real-time feature serving and management
- Feature engineering pipeline integration
- Feature lineage and governance
- Point-in-time correctness for training/inference

### **🔄 Pipeline Orchestrator (Port 8004)**
- DAG-based ML workflow execution
- Resource management and scheduling
- Pipeline monitoring and alerting
- Multi-environment deployment support

### **⚖️ A/B Testing Service (Port 8090)**
- Sophisticated experiment routing and traffic splitting
- Statistical significance testing
- Multi-armed bandit optimization
- Real-time performance monitoring

### **📊 Monitoring & Observability**
- **Prometheus** (Port 9090): Metrics collection and storage
- **Grafana** (Port 3000): Dashboards and visualization
- **AlertManager** (Port 9093): Intelligent alerting system

## 🚀 **Quick Start**

### **1. Deploy Platform Services**
```bash
# Clone the MLOps platform repository
git clone <your-mlops-platform-repo-url>
cd mlops-platform

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Deploy all platform services
docker-compose -f docker-compose.platform.yml up -d

# Verify all services are running
docker-compose ps
```

### **2. Verify Platform Health**
```bash
# Check all service endpoints
curl http://localhost:8000/health/  # Model Registry (requires trailing slash)
curl http://localhost:8003/health   # Experiment Tracking  
curl http://localhost:8002/health   # Feature Store
curl http://localhost:8004/health   # Pipeline Orchestrator
curl http://localhost:8090/health   # A/B Testing
curl http://localhost:9090/-/healthy # Prometheus
curl http://localhost:3000/api/health # Grafana
```

### **3. Access Platform APIs & Documentation**
- **Model Registry API**: http://localhost:8000/docs
- **Experiment Tracking API**: http://localhost:8003/docs  
- **Feature Store API**: http://localhost:8002/docs
- **Pipeline Orchestrator API**: http://localhost:8004/docs
- **A/B Testing API**: http://localhost:8090/docs
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

## 🏢 **Enterprise Architecture**

### **Service Mesh Design**
```
┌─────────────────────────────────────────────────────────┐
│                    MLOps Platform                      │
├─────────────────────────────────────────────────────────┤
│  Model Registry  │  Experiment    │  Feature Store     │
│  (Port 8000)     │  Tracking      │  (Port 8002)       │
│                  │  (Port 8003)   │                    │
├─────────────────────────────────────────────────────────┤
│  Pipeline        │  A/B Testing   │  Monitoring Stack  │
│  Orchestrator    │  (Port 8090)   │  (Prometheus/      │
│  (Port 8004)     │                │   Grafana)         │
└─────────────────────────────────────────────────────────┘
                            ↑
                    External Applications
              (Healthcare AI, FinTech AI, Retail AI, etc.)
```

### **Integration Patterns**
Applications integrate with the platform through:

1. **REST APIs** - Standard HTTP endpoints for all services
2. **Environment Variables** - Service discovery configuration
3. **Docker Networks** - Internal communication
4. **Kubernetes Services** - Cloud-native deployments
5. **Event Streaming** - Real-time data pipelines

## 🔧 **Application Integration Guide**

### **Environment Variables for Client Applications**
```bash
# Service Discovery Configuration
MLOPS_MODEL_REGISTRY_URL=http://localhost:8000
MLOPS_EXPERIMENT_TRACKING_URL=http://localhost:8003
MLOPS_FEATURE_STORE_URL=http://localhost:8002
MLOPS_PIPELINE_ORCHESTRATOR_URL=http://localhost:8004
MLOPS_AB_TESTING_URL=http://localhost:8090

# Monitoring Configuration
MLOPS_PROMETHEUS_URL=http://localhost:9090
MLOPS_GRAFANA_URL=http://localhost:3000

# Authentication (when enabled)
MLOPS_API_KEY=${MLOPS_API_KEY}
MLOPS_SERVICE_TOKEN=${MLOPS_SERVICE_TOKEN}
```

### **Docker Network Integration**
```yaml
# In your application's docker-compose.yml
version: '3.8'

services:
  your-ml-app:
    build: .
    environment:
      - MLOPS_MODEL_REGISTRY_URL=http://model-registry:8000
      - MLOPS_EXPERIMENT_TRACKING_URL=http://experiment-tracking:8003
    networks:
      - mlops-platform-network

networks:
  mlops-platform-network:
    external: true
```

### **Kubernetes Integration**
```yaml
# Application deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: your-ml-app
spec:
  template:
    spec:
      containers:
      - name: app
        env:
        - name: MLOPS_MODEL_REGISTRY_URL
          value: "http://model-registry-service.mlops-platform:8000"
        - name: MLOPS_EXPERIMENT_TRACKING_URL
          value: "http://experiment-tracking-service.mlops-platform:8003"
```

## 📋 **API Documentation**

### **Model Registry API**
```bash
# Register a new model
POST /api/models
{
  "name": "my-classifier-v1",
  "version": "1.0.0", 
  "framework": "scikit-learn",
  "metrics": {"accuracy": 0.95, "f1_score": 0.92},
  "tags": ["production", "healthcare"]
}

# Get model information
GET /api/models/my-classifier-v1/versions/1.0.0

# List all models
GET /api/models?tags=production

# Download model artifacts
GET /api/models/my-classifier-v1/versions/1.0.0/download
```

### **Experiment Tracking API**
```bash
# Create experiment
POST /api/experiments
{
  "name": "model-optimization-2024",
  "description": "Hyperparameter tuning for classifier performance"
}

# Start a run
POST /api/experiments/{experiment_id}/runs
{
  "run_name": "lstm_dropout_0.3",
  "parameters": {"learning_rate": 0.001, "batch_size": 32}
}

# Log metrics
POST /api/experiments/{experiment_id}/runs/{run_id}/metrics
{
  "accuracy": 0.95,
  "precision": 0.92,
  "recall": 0.98,
  "step": 100
}
```

### **Feature Store API**
```bash
# Create feature set
POST /api/feature-sets
{
  "name": "user_features",
  "description": "User demographic and behavioral features",
  "features": [
    {"name": "age", "type": "int"},
    {"name": "avg_session_duration", "type": "float"}
  ]
}

# Serve features for online inference
GET /api/features/serve?entities=user_123&features=age,avg_session_duration
```

### **A/B Testing API**
```bash
# Create experiment
POST /api/experiments
{
  "name": "model_v2_test",
  "variants": [
    {"name": "control", "weight": 0.5, "model_version": "v1.0"},
    {"name": "treatment", "weight": 0.5, "model_version": "v2.0"}
  ]
}

# Route user to variant
GET /api/route?user_id=user_123&experiment=model_v2_test
```

## 🔒 **Security & Compliance**

### **Authentication & Authorization**
- **API Key Authentication** for service-to-service communication
- **Role-Based Access Control (RBAC)** for resource permissions
- **Service Mesh mTLS** for encrypted inter-service communication

### **Data Protection**
- **Encryption at Rest** for all stored artifacts and metadata
- **TLS 1.3** for all API communications
- **Audit Logging** for all operations with full traceability

### **Secret Management**
```bash
# Use environment variables for all sensitive configuration
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD}
API_SECRET_KEY=${API_SECRET_KEY}
```

## 🚀 **Deployment Options**

### **Docker Compose (Development/Testing)**
```bash
# Quick development setup
docker-compose -f docker-compose.platform.yml up -d
```

### **Kubernetes (Production)**
```bash
# Deploy to staging environment
kubectl apply -f deployment/k8s/environments/staging/

# Deploy to production environment
kubectl apply -f deployment/k8s/environments/production/
```

## 📊 **Monitoring & Observability**

### **Pre-built Dashboards**
- **Platform Overview**: Service health, performance, and resource utilization
- **Model Performance**: Accuracy trends, latency, and throughput metrics
- **Infrastructure Metrics**: CPU, memory, disk, and network utilization

### **Alert Rules & SLAs**
- **Service Availability**: >99.9% uptime SLA
- **API Response Time**: <200ms 95th percentile
- **Resource Utilization**: Auto-scaling triggers and capacity planning

## 🧪 **Testing & Quality Assurance**

### **Platform Testing Strategy**
```bash
# Comprehensive platform validation
python3 scripts/test_mlops_platform.py --comprehensive

# Service-specific testing
python3 scripts/test_model_registry.py
python3 scripts/test_experiment_tracking.py
python3 scripts/test_feature_store.py
```

### **Quality Metrics**
- **Test Coverage**: Current 90%+ across all services
- **Code Quality**: Automated quality gates with PR blocking
- **Security Score**: Regular security assessments and remediation

## 🔄 **CI/CD Pipeline**

### **Automated Workflow**
1. **Code Commit** → Trigger CI pipeline
2. **Quality Checks** → Code formatting, linting, security scanning
3. **Unit Tests** → Service-specific test suites
4. **Integration Tests** → Cross-service communication testing
5. **Build & Package** → Docker image creation and tagging
6. **Deploy Staging** → Automated staging environment deployment
7. **Deploy Production** → Blue-green production deployment

## 📚 **Documentation & Support**

### **Enterprise Support**
- **24/7 Platform Monitoring** with dedicated support team
- **SLA-backed Service Availability** with escalation procedures
- **Professional Services** for custom integration and optimization

### **Development Environment Setup**
```bash
# Clone and set up development environment
git clone <mlops-platform-repo-url>
cd mlops-platform
make setup-dev

# Run development services
make dev-up

# Run comprehensive tests
make test-all
```

## 🔧 **Troubleshooting**

### **Common Issues**

#### **Redis Connection Failures in Kubernetes**
If you see errors like `redis-cli: command not found` or `Waiting for Redis...` in init containers:

1. **Verify Redis is deployed**: Check if Redis deployment exists in your namespace
   ```bash
   kubectl get deployment redis -n <your-namespace>
   ```

2. **Deploy Redis if missing**: Apply the Redis manifest
   ```bash
   kubectl apply -f deployment/k8s/environments/<env>/redis.yaml
   ```

3. **Verify Redis service**: Ensure the service is accessible
   ```bash
   kubectl run redis-test --rm -it --image=redis:7-alpine --restart=Never -n <your-namespace> -- redis-cli -h redis ping
   ```

## 📄 **License & Legal**

This MLOps platform is licensed under the **MIT License** - see [LICENSE](LICENSE) file for details.

---

## 🎯 **Next Steps for Application Teams**

1. **Deploy the Platform**: Follow the Quick Start guide
2. **Integrate Your Application**: Use the Integration Guide and API documentation
3. **Set Up Monitoring**: Configure dashboards and alerts for your use case
4. **Scale as Needed**: Add compute resources and configure auto-scaling

**Built for enterprise scale, security, and reliability** 🚀