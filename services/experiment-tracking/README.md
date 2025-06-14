# Experiment Tracking 2.0 🧪

A comprehensive experiment management platform that integrates seamlessly with the MLOps ecosystem to provide complete ML experiment lifecycle management.

## 🎯 Overview

Experiment Tracking 2.0 is the fourth pillar of the MLOps platform, providing scientists and engineers with powerful tools to track, compare, and reproduce machine learning experiments. It serves as the central hub for experiment orchestration and connects all other MLOps services.

## 🏗️ Architecture

```
Experiment Tracking 2.0
├── 🧪 Experiment Management (Project organization)
├── 📊 Metrics & Parameters (Performance tracking)
├── 📈 Visualization Engine (Interactive charts)
├── 🔄 Run Orchestration (Execution management)
├── 🔗 MLOps Integration (Service connectivity)
└── 📱 Collaboration Tools (Team sharing)
```

## 🌟 Key Features

### 🧪 Comprehensive Experiment Management
- **Project Organization** - Hierarchical experiment grouping
- **Run Tracking** - Detailed execution history
- **Parameter Logging** - Hyperparameter versioning
- **Metric Collection** - Real-time and batch metrics
- **Artifact Management** - Model and data versioning

### 📊 Advanced Analytics
- **Interactive Visualizations** - Charts, plots, and dashboards
- **Experiment Comparison** - Side-by-side analysis
- **Statistical Analysis** - Significance testing
- **Performance Trends** - Historical analysis
- **Resource Usage** - Cost and compute tracking

### 🔄 MLOps Platform Integration
- **Model Registry** - Automatic model registration
- **Pipeline Orchestrator** - Experiment pipeline execution
- **Feature Store** - Feature usage tracking
- **Healthcare AI** - Domain-specific experiment types

### 🤝 Collaboration & Reproducibility
- **Team Sharing** - Multi-user experiment access
- **Reproducible Runs** - Environment and code versioning
- **Experiment Templates** - Standardized workflows
- **Notes & Annotations** - Rich documentation

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL 12+
- Redis 6+ (optional, for caching)
- MinIO/S3 (for artifact storage)

### Installation

```bash
# Navigate to experiment tracking service
cd services/experiment-tracking

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://user:pass@localhost:5432/experiment_tracking"
export REDIS_URL="redis://localhost:6379"
export MINIO_ENDPOINT="localhost:9000"
export MINIO_ACCESS_KEY="minioadmin"
export MINIO_SECRET_KEY="minioadmin"
```

### Start the Service

```bash
# Start Experiment Tracking
python3 main.py

# Service runs on port 8003
# API documentation: http://localhost:8003/docs
```

## 📚 API Reference

### Project Management

```python
# Create a new project
POST /api/v1/projects
{
    "name": "healthcare-ai-experiments",
    "description": "Healthcare AI model development",
    "team": "ml-team",
    "tags": ["healthcare", "classification"]
}

# List projects
GET /api/v1/projects?team=ml-team&tag=healthcare

# Get project details
GET /api/v1/projects/{project_id}
```

### Experiment Management

```python
# Create experiment
POST /api/v1/experiments
{
    "project_id": "uuid",
    "name": "baseline-model-v1",
    "description": "Initial healthcare classification model",
    "hypothesis": "TF-IDF + MultinomialNB will achieve >95% accuracy",
    "tags": ["baseline", "sklearn"]
}

# Start experiment run
POST /api/v1/experiments/{experiment_id}/runs
{
    "name": "run-001",
    "parameters": {
        "algorithm": "MultinomialNB",
        "alpha": 0.1,
        "max_features": 10000
    },
    "environment": {
        "python_version": "3.9.6",
        "sklearn_version": "1.3.0"
    }
}
```

### Metrics & Logging

```python
# Log metrics during training
POST /api/v1/runs/{run_id}/metrics
{
    "metrics": {
        "accuracy": 0.952,
        "f1_score": 0.934,
        "precision": 0.945,
        "recall": 0.924,
        "training_loss": 0.234
    },
    "step": 100,
    "timestamp": "2024-01-15T10:30:00Z"
}

# Log artifacts
POST /api/v1/runs/{run_id}/artifacts
{
    "name": "model.pkl",
    "path": "s3://experiments/run-001/model.pkl",
    "type": "model",
    "size_bytes": 1024000,
    "metadata": {
        "framework": "sklearn",
        "model_type": "MultinomialNB"
    }
}

# Real-time metric streaming
WebSocket /api/v1/runs/{run_id}/metrics/stream
```

## 🔄 MLOps Integration Workflows

### 1. Healthcare AI Experiment Workflow
```python
# Healthcare-specific experiment template
healthcare_experiment = {
    "name": "healthcare-classifier-optimization",
    "type": "classification",
    "domain": "healthcare",
    "metrics": [
        "accuracy", "f1_score", "precision", "recall",
        "crisis_detection_rate", "response_quality_score"
    ],
    "validation_criteria": {
        "accuracy": ">= 0.95",
        "crisis_detection_rate": ">= 0.99"
    },
    "model_registry_integration": {
        "auto_register": True,
        "promotion_criteria": "validation_passed"
    }
}
```

### 2. Pipeline Integration
```python
# Automatic experiment creation from pipeline
pipeline_config = {
    "name": "healthcare-training-pipeline",
    "experiment_tracking": {
        "project_id": "healthcare-ai",
        "auto_create_experiment": True,
        "track_metrics": ["accuracy", "loss"],
        "track_artifacts": ["model", "preprocessor"]
    },
    "tasks": [
        {
            "name": "train-model",
            "operator": "model_training",
            "experiment_config": {
                "log_parameters": True,
                "log_metrics": True,
                "log_artifacts": True
            }
        }
    ]
}
```

### 3. Model Registry Integration
```python
# Automatic model registration from experiments
@experiment.on_completion
def register_best_model(experiment_id):
    # Get best run based on criteria
    best_run = experiment_tracker.get_best_run(
        experiment_id=experiment_id,
        metric="accuracy",
        mode="max"
    )
    
    # Register in Model Registry
    model_registry.register_model(
        name=f"healthcare-classifier-{experiment_id}",
        run_id=best_run.id,
        artifacts=best_run.artifacts,
        metrics=best_run.metrics,
        parameters=best_run.parameters
    )
```

## 📊 Advanced Features

### Experiment Comparison

```python
# Compare multiple experiments
POST /api/v1/experiments/compare
{
    "experiment_ids": ["exp-1", "exp-2", "exp-3"],
    "metrics": ["accuracy", "f1_score"],
    "visualization": "parallel_coordinates"
}

# Response includes statistical analysis
{
    "comparison_id": "comp-uuid",
    "results": {
        "best_experiment": "exp-2",
        "statistical_significance": {
            "accuracy": {"p_value": 0.032, "significant": true}
        },
        "visualization_url": "/visualizations/comp-uuid"
    }
}
```

### Hyperparameter Optimization

```python
# HPO experiment
POST /api/v1/experiments/{experiment_id}/hpo
{
    "search_space": {
        "alpha": {"type": "float", "min": 0.01, "max": 1.0},
        "max_features": {"type": "int", "min": 1000, "max": 50000}
    },
    "optimization": {
        "algorithm": "bayesian",
        "metric": "accuracy",
        "mode": "maximize",
        "max_trials": 100
    },
    "early_stopping": {
        "patience": 10,
        "min_delta": 0.001
    }
}
```

### Real-time Monitoring

```python
# Live experiment dashboard
GET /api/v1/experiments/{experiment_id}/dashboard

# Real-time metrics stream
WebSocket /api/v1/experiments/{experiment_id}/metrics/live
{
    "run_id": "run-001",
    "metrics": {
        "step": 150,
        "accuracy": 0.954,
        "loss": 0.218
    },
    "timestamp": "2024-01-15T10:35:00Z"
}
```

## 🎯 Healthcare AI Integration

### Domain-Specific Metrics

```python
# Healthcare-specific experiment metrics
healthcare_metrics = {
    "ml_metrics": {
        "accuracy": 0.952,
        "f1_score": 0.934,
        "auc_roc": 0.967
    },
    "healthcare_metrics": {
        "crisis_detection_rate": 0.995,
        "response_appropriateness": 0.887,
        "medical_disclaimer_compliance": 1.0,
        "empathy_score": 0.734
    },
    "safety_metrics": {
        "false_crisis_rate": 0.002,
        "missed_crisis_rate": 0.005,
        "response_safety_score": 0.956
    }
}
```

### Experiment Templates

```python
# Healthcare classification template
healthcare_template = {
    "name": "Healthcare Classification Experiment",
    "parameters": {
        "required": ["algorithm", "training_data"],
        "optional": ["max_features", "alpha", "test_size"]
    },
    "metrics": [
        "accuracy", "f1_score", "precision", "recall",
        "crisis_detection_rate", "response_quality"
    ],
    "validation": {
        "required_accuracy": 0.95,
        "required_crisis_detection": 0.99
    },
    "artifacts": ["model", "preprocessor", "confusion_matrix"]
}
```

## 🏢 Enterprise Features

### 🔐 Security & Governance
- Project-based access control
- Experiment audit trails
- Secure artifact storage
- Data lineage tracking

### 📈 Analytics & Reporting
- Team productivity metrics
- Resource utilization reports
- Experiment success rates
- Cost analysis

### 🔄 Integration & Automation
- CI/CD pipeline integration
- Slack/Teams notifications
- Auto-scaling for HPO
- Scheduled experiment runs

## 🔧 Configuration

### Environment Variables

```bash
# Application settings
DEBUG=false
HOST=0.0.0.0
PORT=8003
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://user:pass@host:5432/db
DATABASE_POOL_SIZE=20

# Redis (optional)
REDIS_URL=redis://localhost:6379
REDIS_TTL=3600

# Storage (MinIO/S3)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
STORAGE_BUCKET_EXPERIMENTS=experiments
STORAGE_BUCKET_ARTIFACTS=artifacts

# MLOps Integration
MODEL_REGISTRY_URL=http://localhost:8000
PIPELINE_ORCHESTRATOR_URL=http://localhost:8001
FEATURE_STORE_URL=http://localhost:8002

# Visualization
ENABLE_REAL_TIME_PLOTS=true
PLOT_BACKEND=plotly
MAX_CONCURRENT_VISUALIZATIONS=50
```

## 🧪 Testing

```bash
# Validate service structure
python3 validate_experiment_tracking.py

# Run unit tests
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# API integration tests
pytest tests/api/
```

## 📈 Metrics & Monitoring

The service exposes comprehensive metrics:

- **Experiment counts** by project, team, status
- **Resource usage** for training runs
- **Success rates** and completion times
- **User activity** and collaboration metrics
- **Storage usage** and artifact counts

## 🔮 Roadmap

### Phase 1: Core Platform ✅
- [x] Experiment and run management
- [x] Parameter and metric tracking
- [x] Basic visualization
- [x] MLOps service integration

### Phase 2: Advanced Features 🚧
- [ ] Hyperparameter optimization
- [ ] Advanced visualizations
- [ ] Real-time collaboration
- [ ] Automated experiment analysis

### Phase 3: AI-Powered Insights 📋
- [ ] Experiment recommendation engine
- [ ] Automated hyperparameter tuning
- [ ] Predictive experiment outcomes
- [ ] Intelligent resource allocation

## 🤝 Integration Examples

### With Model Registry
```python
# Auto-register best models
experiment_tracker.register_model_promotion_hook(
    experiment_id="healthcare-exp-1",
    criteria={"accuracy": ">= 0.95"},
    registry_url="http://model-registry:8000"
)
```

### With Pipeline Orchestrator
```python
# Trigger pipeline from experiment
orchestrator.trigger_pipeline(
    pipeline_id="training-pipeline",
    experiment_context={
        "experiment_id": "exp-123",
        "run_id": "run-456"
    }
)
```

### With Feature Store
```python
# Track feature usage in experiments
experiment_tracker.log_feature_usage(
    run_id="run-123",
    feature_sets=["user_features", "context_features"],
    feature_importance=feature_importance_scores
)
```

---

**Experiment Tracking 2.0** - *Complete ML Experiment Management* 🧪