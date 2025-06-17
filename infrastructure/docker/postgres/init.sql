-- Initialize MLOps databases
-- WARNING: This file should not contain hardcoded passwords
-- Use init-template.sql with environment variable substitution instead
-- For development, set MLFLOW_PASSWORD environment variable
CREATE USER mlflow WITH PASSWORD 'mLHWDctQyjwPXqKlrRv6Gg==';
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

-- Model Registry tables will be created by SQLAlchemy migrations
\c model_registry;

-- Initialize Pipeline Orchestrator database
\c pipeline_orchestrator;

CREATE TABLE IF NOT EXISTS pipelines (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    config JSONB,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id SERIAL PRIMARY KEY,
    pipeline_id INTEGER REFERENCES pipelines(id),
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    logs TEXT,
    metrics JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance

\c pipeline_orchestrator;
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs(status);

-- Sample data will be managed by the Model Registry service

-- Insert sample data in Pipeline Orchestrator
\c pipeline_orchestrator;
INSERT INTO pipelines (name, description, config)
VALUES 
    ('demo-llm-training', 'Training pipeline for demo LLM model', 
     '{"stages": ["data_prep", "training", "evaluation", "deployment"], "trigger": "manual"}'),
    ('model-deployment', 'Model deployment pipeline', 
     '{"stages": ["validation", "staging", "production"], "trigger": "automatic"}')
ON CONFLICT DO NOTHING;