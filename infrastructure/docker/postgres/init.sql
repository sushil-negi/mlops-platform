-- Initialize MLOps databases
CREATE USER mlflow WITH PASSWORD 'mlflow123';
CREATE DATABASE mlflow OWNER mlflow;
CREATE DATABASE model_registry OWNER mlops;
CREATE DATABASE experiment_tracking OWNER mlops;
CREATE DATABASE feature_store OWNER mlops;
CREATE DATABASE pipeline_orchestrator OWNER mlops;
CREATE DATABASE ab_testing OWNER mlops;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE mlflow TO mlflow;
GRANT ALL PRIVILEGES ON DATABASE model_registry TO mlops;
GRANT ALL PRIVILEGES ON DATABASE experiment_tracking TO mlops;
GRANT ALL PRIVILEGES ON DATABASE feature_store TO mlops;
GRANT ALL PRIVILEGES ON DATABASE pipeline_orchestrator TO mlops;
GRANT ALL PRIVILEGES ON DATABASE ab_testing TO mlops;

-- Create schemas for different services
\c mlflow;

-- Model Registry tables
CREATE SCHEMA IF NOT EXISTS model_registry;

CREATE TABLE IF NOT EXISTS model_registry.models (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    version VARCHAR(100) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    artifact_path TEXT,
    performance_metrics JSONB,
    UNIQUE(name, version)
);

CREATE TABLE IF NOT EXISTS model_registry.deployments (
    id SERIAL PRIMARY KEY,
    model_id INTEGER REFERENCES model_registry.models(id),
    environment VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    endpoint_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    config JSONB
);

-- Pipeline Orchestrator tables
CREATE SCHEMA IF NOT EXISTS pipeline_orchestrator;

CREATE TABLE IF NOT EXISTS pipeline_orchestrator.pipelines (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    config JSONB,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pipeline_orchestrator.pipeline_runs (
    id SERIAL PRIMARY KEY,
    pipeline_id INTEGER REFERENCES pipeline_orchestrator.pipelines(id),
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    logs TEXT,
    metrics JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Monitoring tables
CREATE SCHEMA IF NOT EXISTS monitoring;

CREATE TABLE IF NOT EXISTS monitoring.model_metrics (
    id SERIAL PRIMARY KEY,
    model_id INTEGER,
    metric_name VARCHAR(255) NOT NULL,
    metric_value DOUBLE PRECISION,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    environment VARCHAR(50),
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS monitoring.alerts (
    id SERIAL PRIMARY KEY,
    model_id INTEGER,
    alert_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) DEFAULT 'medium',
    message TEXT,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_models_name_version ON model_registry.models(name, version);
CREATE INDEX IF NOT EXISTS idx_deployments_model_env ON model_registry.deployments(model_id, environment);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_orchestrator.pipeline_runs(status);
CREATE INDEX IF NOT EXISTS idx_model_metrics_timestamp ON monitoring.model_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON monitoring.alerts(status);

-- Insert sample data
INSERT INTO model_registry.models (name, version, description, status, metadata, performance_metrics) 
VALUES 
    ('demo-llm', '1.0.0', 'Demo Language Model for MLOps showcase', 'production', 
     '{"architecture": "GPT-2", "parameters": "124M", "training_data": "demo_dataset"}',
     '{"accuracy": 0.95, "latency_ms": 100, "throughput_rps": 10}')
ON CONFLICT (name, version) DO NOTHING;

INSERT INTO pipeline_orchestrator.pipelines (name, description, config)
VALUES 
    ('demo-llm-training', 'Training pipeline for demo LLM model', 
     '{"stages": ["data_prep", "training", "evaluation", "deployment"], "trigger": "manual"}'),
    ('model-deployment', 'Model deployment pipeline', 
     '{"stages": ["validation", "staging", "production"], "trigger": "automatic"}')
ON CONFLICT DO NOTHING;