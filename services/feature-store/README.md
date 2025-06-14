# Feature Store 2.0 🏪

A production-grade, real-time feature management platform for MLOps that provides centralized feature storage, versioning, and serving capabilities.

## 🎯 Overview

Feature Store 2.0 is an enterprise-ready feature management system that serves as the single source of truth for all ML features. It bridges the gap between data engineering and ML engineering by providing consistent feature computation, storage, and serving across training and inference.

## 🏗️ Architecture

```
Feature Store 2.0
├── 📊 Feature Registry (Centralized feature definitions)
├── 💾 Offline Store (Historical feature storage)
├── ⚡ Online Store (Low-latency serving)
├── 🔄 Materialization Engine (Feature computation)
├── 🚀 Serving Layer (Real-time & batch serving)
└── 📈 Monitoring (Usage tracking & quality metrics)
```

## 🌟 Key Features

### 📊 Feature Management
- **Centralized Registry** - Single source of truth for feature definitions
- **Version Control** - Track feature evolution and lineage
- **Feature Discovery** - Search and explore available features
- **Schema Validation** - Ensure data quality and consistency

### 💾 Dual Storage Architecture
- **Offline Store** - Parquet files on S3/MinIO for training data
- **Online Store** - Redis for low-latency serving (<10ms)
- **Point-in-Time Correctness** - Prevent data leakage in training
- **Time Travel** - Access historical feature values

### 🔄 Feature Computation
- **SQL & Python Transformations** - Flexible feature engineering
- **Windowed Aggregations** - Time-based feature calculations
- **Scheduled Materialization** - Automated feature updates
- **Incremental Processing** - Efficient computation

### 🚀 Serving Capabilities
- **Real-time Serving** - Sub-10ms feature retrieval
- **Batch Serving** - Large-scale feature generation
- **Multi-Entity Support** - Complex feature joins
- **Feature Monitoring** - Track usage and performance

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL 12+
- Redis 6+
- MinIO or S3
- Docker (optional)

### Installation

```bash
# Clone the repository
git clone <your-repo>
cd services/feature-store

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://user:pass@localhost:5432/feature_store"
export REDIS_URL="redis://localhost:6379"
export S3_ENDPOINT="http://localhost:9000"
export S3_ACCESS_KEY="minioadmin"
export S3_SECRET_KEY="minioadmin"
```

### Start the Service

```bash
# Run database migrations (if needed)
alembic upgrade head

# Start Feature Store
python3 main.py

# Service runs on port 8002
# API docs: http://localhost:8002/docs
```

## 📚 Usage Guide

### 1. Create a Feature Set

```python
POST /api/v1/feature-sets
{
    "name": "user_profile",
    "description": "User demographic and behavioral features",
    "owner": "data-team",
    "entities": ["user"],
    "source_type": "batch",
    "offline_enabled": true,
    "online_enabled": true,
    "materialization_schedule": "0 */6 * * *"
}
```

### 2. Define Features

```python
POST /api/v1/features
{
    "name": "user_age",
    "feature_set_id": "feature-set-uuid",
    "description": "User age in years",
    "data_type": "int",
    "transformation": "EXTRACT(YEAR FROM AGE(current_date, date_of_birth))",
    "validation_rules": {
        "min_value": 0,
        "max_value": 150
    }
}
```

### 3. Materialize Features

```python
POST /api/v1/feature-sets/{id}/materialize
{
    "start_date": "2024-01-01T00:00:00",
    "end_date": "2024-01-31T23:59:59"
}
```

### 4. Serve Features Online

```python
POST /api/v1/serving/online
{
    "feature_sets": ["user_profile", "user_activity"],
    "entities": {
        "user": ["user_123", "user_456"]
    },
    "features": ["user_age", "purchase_count", "last_login"]
}

# Response
{
    "features": {
        "user_123": {
            "user_age": 28,
            "purchase_count": 156,
            "last_login": "2024-01-15T14:30:00"
        },
        "user_456": {
            "user_age": 35,
            "purchase_count": 89,
            "last_login": "2024-01-14T09:15:00"
        }
    },
    "metadata": {
        "latency_ms": 3.2,
        "cache_hit": true
    }
}
```

### 5. Get Historical Features

```python
POST /api/v1/serving/historical
{
    "feature_sets": ["user_profile"],
    "entity_df": {
        "columns": ["user_id", "event_timestamp"],
        "data": [
            ["user_123", "2024-01-01T10:00:00"],
            ["user_456", "2024-01-01T11:00:00"]
        ]
    },
    "features": ["user_age", "purchase_count"]
}
```

## 🛠️ Feature Types

### Basic Features
```python
# Numeric feature
{
    "name": "account_balance",
    "data_type": "float",
    "default_value": 0.0
}

# Categorical feature
{
    "name": "user_segment",
    "data_type": "string",
    "allowed_values": ["premium", "standard", "basic"]
}
```

### Aggregated Features
```python
# Time-windowed aggregation
{
    "name": "purchases_last_30d",
    "data_type": "int",
    "transformation": "COUNT(*) OVER (PARTITION BY user_id ORDER BY timestamp RANGE BETWEEN INTERVAL '30 days' PRECEDING AND CURRENT ROW)",
    "window_size": "30d"
}
```

### Composite Features
```python
# Derived from multiple features
{
    "name": "purchase_frequency",
    "data_type": "float",
    "transformation": "purchases_last_30d / NULLIF(days_since_signup, 0)",
    "source_features": ["purchases_last_30d", "days_since_signup"]
}
```

## 📊 Data Flow

### Training Pipeline
```
1. Define Features → 2. Materialize Offline → 3. Generate Training Data → 4. Train Model
```

### Serving Pipeline
```
1. Request Features → 2. Check Cache → 3. Fetch from Store → 4. Return Features
```

### Materialization Pipeline
```
1. Read Source Data → 2. Apply Transformations → 3. Validate Quality → 4. Update Stores
```

## 🔧 Configuration

### Storage Backends

```python
# S3/MinIO Configuration
STORAGE_BACKEND=s3
S3_ENDPOINT=http://minio:9000
S3_BUCKET=feature-store
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin

# Local File System
STORAGE_BACKEND=local
STORAGE_PATH=/data/feature-store
```

### Compute Engines

```python
# DuckDB (Default - embedded)
COMPUTE_ENGINE=duckdb
MAX_COMPUTE_THREADS=4

# Apache Spark (Distributed)
COMPUTE_ENGINE=spark
SPARK_MASTER=spark://master:7077
```

### Caching

```python
# Redis Configuration
REDIS_URL=redis://localhost:6379
SERVING_CACHE_ENABLED=true
SERVING_CACHE_TTL=300  # 5 minutes
```

## 📈 Monitoring

### Metrics Endpoints

```bash
# System metrics
GET /monitoring/metrics

# Feature statistics
GET /monitoring/statistics?days=7

# Data freshness
GET /monitoring/data-freshness

# Usage metrics
GET /monitoring/usage?start_date=2024-01-01
```

### Key Metrics

- **Serving Latency** - P50, P95, P99 response times
- **Cache Hit Rate** - Percentage of cached responses
- **Feature Coverage** - Percentage of entities with features
- **Data Freshness** - Age of materialized features
- **Compute Cost** - Resources used for materialization

## 🏢 Enterprise Features

### 🔐 Security
- API key authentication
- Feature-level access control
- Audit logging
- Encryption at rest

### 📈 Scalability
- Horizontal scaling for serving
- Distributed compute for materialization
- Partitioned storage
- Connection pooling

### 🚨 Reliability
- Health checks and readiness probes
- Automatic retries
- Circuit breakers
- Graceful degradation

### 💰 Cost Optimization
- Tiered storage (hot/warm/cold)
- Intelligent caching
- Compute resource optimization
- Usage-based retention

## 🔄 Integration

### ML Frameworks
```python
# Scikit-learn
features_df = feature_store.get_historical_features(
    entities=train_df[["user_id", "timestamp"]],
    features=["user_age", "purchase_count"]
)
X_train = features_df[feature_list]

# TensorFlow
feature_columns = [
    tf.feature_column.numeric_column("user_age"),
    tf.feature_column.numeric_column("purchase_count")
]
```

### Data Platforms
- **Databricks** - Native Delta Lake support
- **Snowflake** - External table integration
- **BigQuery** - Federated queries
- **Kafka** - Stream processing

### MLOps Platforms
- **Model Registry** - Feature metadata in model versions
- **Pipeline Orchestrator** - Feature materialization jobs
- **Experiment Tracking** - Feature importance logging

## 🧪 Testing

```bash
# Run unit tests
pytest tests/unit

# Run integration tests
pytest tests/integration

# Run load tests
pytest tests/load
```

## 🔮 Roadmap

### Phase 1: Core Platform ✅
- [x] Feature registry and versioning
- [x] Offline and online stores
- [x] Basic materialization
- [x] REST API

### Phase 2: Advanced Features 🚧
- [ ] Streaming features
- [ ] Feature monitoring UI
- [ ] Automated backfilling
- [ ] Feature quality metrics

### Phase 3: Enterprise Scale 📋
- [ ] Multi-region support
- [ ] Advanced security (RBAC, encryption)
- [ ] Cost tracking and optimization
- [ ] SLA guarantees

### Phase 4: AI-Powered Features 🎯
- [ ] Automated feature discovery
- [ ] Feature importance analysis
- [ ] Anomaly detection
- [ ] Smart caching

## 🤝 Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for development guidelines.

## 📄 License

This project is part of the MLOps Platform suite.

---

**Feature Store 2.0** - *The Foundation of Feature Engineering* 🏪