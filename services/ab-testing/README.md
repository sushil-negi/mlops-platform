# Healthcare AI A/B Testing Service

Safe experimentation framework for healthcare AI models with automatic safety monitoring.

## Features

- **Safe Model Comparison**: Compare healthcare AI models with automatic safety thresholds
- **Real-time Safety Monitoring**: Continuous monitoring with emergency stop capabilities  
- **Statistical Analysis**: Comprehensive statistical analysis with healthcare-specific recommendations
- **Traffic Routing**: Consistent user routing based on configurable traffic splits
- **Metrics Collection**: Detailed metrics collection and aggregation
- **Integration**: Seamless integration with Prometheus, Alertmanager, and Redis

## Quick Start

```bash
# Start the service
docker-compose up -d

# Create an experiment
curl -X POST http://localhost:8080/experiments \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Crisis Detection Model Comparison",
    "description": "Testing improved crisis detection model",
    "model_a": "healthcare-ai-v1.2",
    "model_b": "healthcare-ai-v1.3-crisis",
    "traffic_split": 80,
    "created_by": "data-scientist"
  }'

# Start the experiment
curl -X POST http://localhost:8080/experiments/{experiment_id}/start

# Get routing decision for a user
curl http://localhost:8080/route/user123

# View experiment results
curl http://localhost:8080/experiments/{experiment_id}/results
```

## Safety Thresholds

- **Crisis Detection Rate**: ≥99% (CRITICAL - auto-stop if violated)
- **Empathy Score**: ≥65% 
- **Accuracy**: ≥90%
- **Response Time**: ≤500ms (95th percentile)

## API Endpoints

- `POST /experiments` - Create new experiment
- `POST /experiments/{id}/start` - Start experiment
- `GET /route/{user_id}` - Get model routing
- `POST /experiments/{id}/metrics` - Log metrics
- `GET /experiments/{id}/results` - Get results
- `POST /experiments/{id}/stop` - Stop experiment
- `POST /experiments/{id}/emergency-stop` - Emergency stop

## Configuration

Environment variables:
- `REDIS_URL`: Redis connection string
- `PROMETHEUS_URL`: Prometheus endpoint
- `ALERTMANAGER_URL`: Alertmanager endpoint
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)