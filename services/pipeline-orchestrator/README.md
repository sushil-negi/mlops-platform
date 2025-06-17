# Pipeline Orchestrator 2.0 🚀

An intelligent, enterprise-ready pipeline orchestration engine designed specifically for MLOps workflows.

## 🎯 Overview

Pipeline Orchestrator 2.0 is a production-grade workflow engine that orchestrates complex ML pipelines with intelligent resource management, fault tolerance, and enterprise-level features. Built for modern MLOps platforms, it provides a complete solution for automating data science and machine learning workflows.

## 🏗️ Architecture

```
Pipeline Orchestrator 2.0
├── 🧠 Intelligent Scheduler (Resource-aware scheduling)
├── ⚙️  Task Executor (ML-specific operators)
├── 📊 Resource Manager (Dynamic allocation)
├── 🔄 DAG Engine (Workflow definition)
├── 🔌 REST API (Pipeline management)
└── 📈 Monitoring (Real-time metrics)
```

## 🌟 Key Features

### 🧠 Intelligent Scheduling
- **Resource-aware scheduling** - Optimal task placement based on CPU, memory, GPU availability
- **Concurrent execution** - Multiple pipelines with configurable limits
- **Smart retry policies** - Exponential backoff and failure recovery
- **Dynamic load balancing** - Automatic resource optimization

### ⚙️ ML-Specific Operators
- **Data Ingestion** - Multi-source data loading with validation
- **Data Validation** - Quality checks with configurable thresholds
- **Model Training** - Framework-agnostic ML training orchestration
- **Model Registration** - Automatic model registry integration
- **Custom Scripts** - Flexible execution environment

### 📊 Resource Management
- **Dynamic allocation** - Real-time resource monitoring and allocation
- **Performance optimization** - Resource usage recommendations
- **Cost tracking** - Compute cost estimation and monitoring
- **GPU support** - Intelligent GPU allocation for ML workloads

### 🔄 Advanced DAG Engine
- **Cycle detection** - Automatic validation of pipeline dependencies
- **Flexible triggers** - Manual, scheduled, and event-driven execution
- **Conditional execution** - Smart branching based on task outcomes
- **Pipeline templates** - Reusable workflow definitions

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL 12+ (for pipeline persistence)
- Redis 6+ (for task queue)
- Docker (optional, for containerized deployment)

### Installation

```bash
# Clone the MLOps platform
git clone <your-repo>
cd services/pipeline-orchestrator

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://user:pass@localhost:5432/orchestrator"
export REDIS_URL="redis://localhost:6379"
export MAX_CONCURRENT_RUNS=10
export MAX_WORKERS=5
```

### Start the Service

```bash
# Start Pipeline Orchestrator
python3 main.py

# Service starts on port 8001
# API documentation: http://localhost:8001/docs
```

## 📚 API Reference

### Pipeline Management

```python
# Create a new pipeline
POST /api/v1/pipelines
{
    "name": "ml-training-pipeline",
    "description": "End-to-end ML training workflow",
    "owner": "data-science-team",
    "tasks": [
        {
            "name": "ingest-data",
            "operator": "data_ingestion",
            "parameters": {
                "source_type": "s3",
                "source_path": "s3://data/training-data.csv"
            },
            "cpu": 1.0,
            "memory_gb": 2.0
        },
        {
            "name": "validate-data", 
            "operator": "data_validation",
            "upstream_tasks": ["ingest-data"],
            "parameters": {
                "max_error_rate": 0.05
            },
            "cpu": 0.5,
            "memory_gb": 1.0
        },
        {
            "name": "train-model",
            "operator": "model_training", 
            "upstream_tasks": ["validate-data"],
            "parameters": {
                "model_type": "classification",
                "algorithm": "random_forest",
                "hyperparameters": {
                    "n_estimators": 100,
                    "max_depth": 10
                }
            },
            "cpu": 4.0,
            "memory_gb": 8.0,
            "gpu": 1
        }
    ]
}

# Start pipeline execution
POST /api/v1/runs
{
    "pipeline_id": "pipeline-uuid",
    "parameters": {
        "experiment_name": "baseline-model-v1"
    },
    "triggered_by": "data-scientist"
}

# Monitor execution
GET /api/v1/runs/{run_id}
```

### Pipeline Examples

#### Simple Data Processing Pipeline
```python
{
    "name": "data-processing",
    "tasks": [
        {
            "name": "extract",
            "operator": "data_ingestion",
            "parameters": {"source": "database"}
        },
        {
            "name": "transform", 
            "operator": "custom_script",
            "upstream_tasks": ["extract"],
            "parameters": {
                "script_type": "python",
                "script_content": "# Data transformation logic"
            }
        },
        {
            "name": "load",
            "operator": "data_ingestion", 
            "upstream_tasks": ["transform"],
            "parameters": {"destination": "warehouse"}
        }
    ]
}
```

#### ML Training with Validation Pipeline
```python
{
    "name": "ml-training-with-validation",
    "tasks": [
        {
            "name": "prepare-data",
            "operator": "data_validation",
            "parameters": {"validation_rules": {...}}
        },
        {
            "name": "train-candidate-model",
            "operator": "model_training",
            "upstream_tasks": ["prepare-data"]
        },
        {
            "name": "validate-model-quality",
            "operator": "custom_script",
            "upstream_tasks": ["train-candidate-model"],
            "parameters": {
                "script_content": "# Model validation logic"
            }
        },
        {
            "name": "register-model",
            "operator": "model_registration",
            "upstream_tasks": ["validate-model-quality"],
            "trigger_rule": "all_success"
        }
    ]
}
```

## 🔄 Workflow Patterns

### 1. Linear Pipeline
```
Data Ingestion → Data Validation → Model Training → Model Registration
```

### 2. Parallel Processing
```
Data Ingestion → [Feature Engineering A, Feature Engineering B] → Model Training
```

### 3. Conditional Execution
```
Data Validation → [Success: Model Training, Failure: Data Cleanup]
```

### 4. A/B Testing
```
Data Preparation → [Model A Training, Model B Training] → Model Comparison → Best Model Registration
```

## 🛠️ Operators Reference

### Data Operators

#### data_ingestion
```python
{
    "operator": "data_ingestion",
    "parameters": {
        "source_type": "s3|local|database|api",
        "source_path": "path/to/data",
        "output_path": "path/to/output",
        "format": "json|csv|parquet"
    }
}
```

#### data_validation
```python
{
    "operator": "data_validation", 
    "parameters": {
        "input_path": "path/to/data",
        "validation_rules": {...},
        "max_error_rate": 0.05
    }
}
```

### ML Operators

#### model_training
```python
{
    "operator": "model_training",
    "parameters": {
        "model_type": "classification|regression|clustering",
        "algorithm": "random_forest|svm|neural_network",
        "hyperparameters": {...},
        "training_data_path": "path/to/training/data",
        "min_accuracy": 0.8
    }
}
```

#### model_registration
```python
{
    "operator": "model_registration",
    "parameters": {
        "model_name": "fraud-detection-v1",
        "model_version": "1.0.0", 
        "description": "Model description",
        "tags": ["production", "fraud", "ml"]
    }
}
```

### Utility Operators

#### custom_script
```python
{
    "operator": "custom_script",
    "parameters": {
        "script_type": "python|bash",
        "script_content": "print('Hello, World!')",
        "script_path": "/path/to/script.py"
    }
}
```

## 📊 Monitoring & Observability

### System Metrics
```bash
# Get real-time metrics
GET /monitoring/metrics

# Get detailed health status  
GET /monitoring/health/detailed

# Get execution statistics
GET /monitoring/statistics?days=7
```

### Resource Monitoring
- **CPU, Memory, GPU utilization**
- **Task execution times and throughput**
- **Resource efficiency recommendations**
- **Cost tracking and optimization**

### Pipeline Analytics
- **Success rates and failure analysis**
- **Performance trends and bottlenecks**
- **Resource usage patterns**
- **Operator effectiveness metrics**

## 🏢 Enterprise Features

### 🔐 Security & Governance
- Multi-tenant pipeline organization
- Role-based access control (ready for implementation)
- Comprehensive audit logging
- Secure credential management

### 📈 Scalability & Performance
- Horizontal scaling capabilities
- Resource pooling and optimization
- High-availability design
- Circuit breaker patterns

### 🚨 Reliability & Monitoring
- Health checks and alerting
- Graceful degradation
- Automatic retry and recovery
- Performance monitoring

### 💰 Cost Management
- Resource usage tracking
- Cost estimation and budgeting
- Optimization recommendations
- Resource quota management

## 🔧 Configuration

### Environment Variables

```bash
# Service Configuration
HOST=0.0.0.0
PORT=8001
DEBUG=false
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://user:pass@host:5432/db
DATABASE_POOL_SIZE=20

# Redis Task Queue
REDIS_URL=redis://localhost:6379
REDIS_TASK_QUEUE=mlops_tasks

# Resource Limits
MAX_CONCURRENT_RUNS=10
MAX_WORKERS=5
MAX_CPU_CORES=16
MAX_MEMORY_GB=64
MAX_GPU_COUNT=4

# External Services
MODEL_REGISTRY_URL=http://localhost:8000
FEATURE_STORE_URL=http://localhost:8002

# Storage
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
```

### Advanced Configuration

```python
# Task-specific resource requirements
DEFAULT_TASK_RESOURCES = {
    "data_ingestion": {"cpu": 1.0, "memory_gb": 2.0, "gpu": 0},
    "model_training": {"cpu": 4.0, "memory_gb": 8.0, "gpu": 1},
    "data_validation": {"cpu": 0.5, "memory_gb": 1.0, "gpu": 0}
}

# Retry policies
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_DELAY_SECONDS = 60
ENABLE_CIRCUIT_BREAKER = true

# Monitoring
ENABLE_METRICS = true
ENABLE_TRACING = true
HEARTBEAT_INTERVAL_SECONDS = 30
```

## 🧪 Testing

```bash
# Validate architecture
python3 validate_orchestrator.py

# Run unit tests (when available)
pytest tests/

# API integration tests
pytest tests/integration/

# Load testing
pytest tests/load/
```

## 🔮 Roadmap

### Phase 1: Core Platform ✅
- [x] DAG-based workflow engine
- [x] Intelligent resource scheduling
- [x] ML-specific operators
- [x] REST API for pipeline management

### Phase 2: Advanced Features 🚧
- [ ] Database persistence layer
- [ ] Webhook and event triggers
- [ ] Pipeline templates and marketplace
- [ ] Advanced scheduling (cron, event-based)

### Phase 3: Enterprise Scale 📋
- [ ] Web UI for pipeline visualization
- [ ] Data lineage tracking
- [ ] Advanced security and RBAC
- [ ] Cost optimization and forecasting

### Phase 4: AI-Powered Orchestration 🎯
- [ ] ML-based resource optimization
- [ ] Intelligent pipeline recommendations
- [ ] Predictive failure detection
- [ ] Auto-scaling and self-healing

## 🤝 Integration

### Model Registry Integration
```python
# Automatic model registration after training
{
    "name": "register-trained-model",
    "operator": "model_registration",
    "parameters": {
        "registry_url": "http://model-registry:8000",
        "model_name": "customer-churn-v1"
    }
}
```

### Feature Store Integration
```python
# Feature engineering pipeline
{
    "name": "feature-pipeline",
    "operator": "custom_script",
    "parameters": {
        "script_content": "# Feature store integration code"
    }
}
```

### External ML Platforms
- **MLflow integration** for experiment tracking
- **Kubeflow compatibility** for Kubernetes deployments
- **Apache Airflow migration** tools
- **Custom operator framework** for platform-specific integrations

---

**Pipeline Orchestrator 2.0** - *Intelligent MLOps Workflow Engine* 🚀