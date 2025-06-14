"""
Healthcare AI A/B Testing Service
Manages experiments, routes traffic, and ensures safety
"""

import asyncio
import hashlib
import os
from datetime import datetime
from typing import Dict, List, Optional

import redis.asyncio as redis
import structlog
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Gauge, generate_latest
from prometheus_client.core import CollectorRegistry

try:
    from .metrics import ExperimentMetrics
    from .models import Experiment, ExperimentConfig, ExperimentStatus, RoutingDecision
    from .safety_monitor import SafetyMonitor
    from .statistics import ABTestAnalyzer
except ImportError:
    # Fallback for when running as standalone script
    from statistics import ABTestAnalyzer

    from metrics import ExperimentMetrics
    from safety_monitor import SafetyMonitor

    from models import Experiment, ExperimentConfig, ExperimentStatus, RoutingDecision

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Initialize FastAPI
app = FastAPI(
    title="Healthcare AI A/B Testing Service",
    description="Safe experimentation framework for healthcare AI models",
    version="1.0.0",
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
redis_client: Optional[redis.Redis] = None
safety_monitor: Optional[SafetyMonitor] = None
analyzer: Optional[ABTestAnalyzer] = None
metrics_collector: Optional[ExperimentMetrics] = None

# Prometheus metrics
custom_registry = CollectorRegistry()

experiments_created = Counter(
    "ab_testing_experiments_created_total",
    "Total number of experiments created",
    registry=custom_registry,
)

experiments_active = Gauge(
    "ab_testing_experiments_active",
    "Number of currently active experiments",
    registry=custom_registry,
)

routing_decisions = Counter(
    "ab_testing_routing_decisions_total",
    "Total routing decisions made",
    ["experiment_id", "model"],
    registry=custom_registry,
)

safety_violations = Counter(
    "ab_testing_safety_violations_total",
    "Total safety violations detected",
    ["experiment_id", "metric"],
    registry=custom_registry,
)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global redis_client, safety_monitor, analyzer, metrics_collector

    # Initialize Redis
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    try:
        redis_client = await redis.from_url(redis_url)
        await redis_client.ping()
        logger.info("Connected to Redis", redis_url=redis_url)
    except Exception as e:
        logger.error("Failed to connect to Redis", error=str(e))
        redis_client = None

    # Initialize components
    prometheus_url = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
    alertmanager_url = os.getenv("ALERTMANAGER_URL", "http://localhost:9093")

    safety_monitor = SafetyMonitor(prometheus_url, alertmanager_url)
    analyzer = ABTestAnalyzer()
    metrics_collector = ExperimentMetrics(custom_registry)

    # Set Redis client for metrics collector
    if redis_client:
        await metrics_collector.set_redis_client(redis_client)

    # Start background tasks
    asyncio.create_task(monitor_experiments())

    logger.info("A/B Testing service started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if redis_client:
        await redis_client.close()


async def monitor_experiments():
    """Background task to monitor active experiments"""
    while True:
        try:
            if redis_client:
                # Get all active experiments
                experiments = await get_active_experiments()

                for exp in experiments:
                    # Check safety
                    is_safe = await safety_monitor.check_experiment_safety(exp.id)

                    if not is_safe:
                        logger.warning(
                            "Safety violation detected", experiment_id=exp.id
                        )
                        await emergency_stop_experiment(
                            exp.id, "Safety threshold violation"
                        )

                # Update metrics
                experiments_active.set(len(experiments))

        except Exception as e:
            logger.error("Error in experiment monitoring", error=str(e))

        await asyncio.sleep(10)  # Check every 10 seconds


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    redis_status = False
    if redis_client:
        try:
            await redis_client.ping()
            redis_status = True
        except:
            pass

    return {
        "status": "healthy",
        "redis_connected": redis_status,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/experiments", response_model=Dict)
async def create_experiment(config: ExperimentConfig):
    """Create a new A/B testing experiment"""
    try:
        # Validate safety thresholds
        if config.safety_thresholds.crisis_detection_rate < 0.99:
            raise HTTPException(
                status_code=400, detail="Crisis detection threshold must be >= 99%"
            )

        # Create experiment
        experiment = Experiment(
            id=f"exp_{datetime.utcnow().timestamp()}",
            name=config.name,
            description=config.description,
            model_a=config.model_a,
            model_b=config.model_b,
            traffic_split=config.traffic_split,
            safety_thresholds=config.safety_thresholds,
            status=ExperimentStatus.DRAFT,
            created_at=datetime.utcnow(),
            created_by=config.created_by,
        )

        # Store in Redis
        if redis_client:
            await redis_client.set(
                f"experiment:{experiment.id}",
                experiment.json(),
                ex=86400 * 30,  # 30 days expiry
            )

        # Update metrics
        experiments_created.inc()

        logger.info(
            "Experiment created", experiment_id=experiment.id, name=experiment.name
        )

        return {
            "experiment_id": experiment.id,
            "status": experiment.status,
            "message": "Experiment created successfully",
        }

    except Exception as e:
        logger.error("Failed to create experiment", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/experiments/{experiment_id}/start")
async def start_experiment(experiment_id: str, background_tasks: BackgroundTasks):
    """Start an A/B testing experiment"""
    experiment = await get_experiment(experiment_id)

    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if experiment.status != ExperimentStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start experiment in {experiment.status} status",
        )

    # Validate models exist
    # TODO: Check with MLflow that both models are available

    # Update status
    experiment.status = ExperimentStatus.RUNNING
    experiment.start_time = datetime.utcnow()

    await save_experiment(experiment)

    # Start safety monitoring
    background_tasks.add_task(safety_monitor.start_monitoring, experiment_id)

    logger.info("Experiment started", experiment_id=experiment_id)

    return {"status": "started", "experiment_id": experiment_id}


@app.get("/route/{user_id}")
async def get_routing_decision(
    user_id: str, experiment_id: Optional[str] = None
) -> RoutingDecision:
    """Determine which model a user should use"""

    # If no experiment specified, find active experiments
    if not experiment_id:
        experiments = await get_active_experiments()
        if not experiments:
            return RoutingDecision(
                model="default", experiment_id=None, reason="no_active_experiments"
            )
        experiment = experiments[0]  # Use first active experiment
    else:
        experiment = await get_experiment(experiment_id)

    if not experiment or experiment.status != ExperimentStatus.RUNNING:
        return RoutingDecision(
            model="default", experiment_id=None, reason="experiment_not_running"
        )

    # Consistent routing based on user_id
    hash_value = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
    percentage = hash_value % 100

    if percentage < experiment.traffic_split:
        model = experiment.model_a
        variant = "control"
    else:
        model = experiment.model_b
        variant = "treatment"

    # Update metrics
    routing_decisions.labels(experiment_id=experiment.id, model=variant).inc()

    # Log routing decision
    await log_routing_decision(experiment.id, user_id, model, variant)

    return RoutingDecision(
        model=model,
        experiment_id=experiment.id,
        variant=variant,
        reason="active_experiment",
    )


@app.post("/experiments/{experiment_id}/metrics")
async def log_experiment_metrics(experiment_id: str, metrics: Dict):
    """Log metrics for an experiment"""
    try:
        await metrics_collector.log_metrics(experiment_id, metrics)
        return {"status": "success"}
    except Exception as e:
        logger.error("Failed to log metrics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/experiments/{experiment_id}/results")
async def get_experiment_results(experiment_id: str):
    """Get experiment results and analysis"""
    experiment = await get_experiment(experiment_id)

    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    # Get metrics from Prometheus
    metrics = await metrics_collector.get_experiment_metrics(experiment_id)

    # Perform statistical analysis
    if len(metrics.get("model_a", {}).get("samples", [])) >= 30:
        analysis = analyzer.analyze_experiment(metrics)
    else:
        analysis = {"status": "insufficient_data", "min_samples_needed": 30}

    return {
        "experiment": experiment.dict(),
        "metrics": metrics,
        "analysis": analysis,
        "safety_status": await safety_monitor.get_safety_status(experiment_id),
    }


@app.post("/experiments/{experiment_id}/stop")
async def stop_experiment(experiment_id: str, reason: Optional[str] = None):
    """Stop an A/B testing experiment"""
    experiment = await get_experiment(experiment_id)

    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    experiment.status = ExperimentStatus.COMPLETED
    experiment.end_time = datetime.utcnow()

    await save_experiment(experiment)

    # Generate final report
    results = await get_experiment_results(experiment_id)

    logger.info(
        "Experiment stopped",
        experiment_id=experiment_id,
        reason=reason,
        duration_hours=(experiment.end_time - experiment.start_time).total_seconds()
        / 3600,
    )

    return {"status": "stopped", "reason": reason, "results": results}


@app.post("/experiments/{experiment_id}/emergency-stop")
async def emergency_stop_experiment(experiment_id: str, reason: str):
    """Emergency stop for safety violations"""
    logger.critical(
        "EMERGENCY STOP triggered", experiment_id=experiment_id, reason=reason
    )

    # Stop experiment immediately
    experiment = await get_experiment(experiment_id)
    if experiment:
        experiment.status = ExperimentStatus.FAILED
        experiment.end_time = datetime.utcnow()
        experiment.failure_reason = reason
        await save_experiment(experiment)

    # TODO: Trigger rollback to control model

    return {"status": "emergency_stopped", "reason": reason}


@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(custom_registry)


@app.post("/webhook/alerts")
async def handle_alertmanager_webhook(alerts: Dict):
    """Handle alerts from Alertmanager"""
    try:
        for alert in alerts.get("alerts", []):
            if alert.get("labels", {}).get("alertname") == "ABTestSafetyViolation":
                experiment_id = alert.get("labels", {}).get("experiment_id")
                if experiment_id:
                    logger.critical(
                        "Received safety alert from Alertmanager",
                        experiment_id=experiment_id,
                        alert=alert,
                    )
                    # Emergency stop is already triggered by safety monitor

        return {"status": "acknowledged"}
    except Exception as e:
        logger.error("Failed to process alert webhook", error=str(e))
        return {"status": "error", "message": str(e)}


# Helper functions
async def get_experiment(experiment_id: str) -> Optional[Experiment]:
    """Get experiment from storage"""
    if not redis_client:
        return None

    data = await redis_client.get(f"experiment:{experiment_id}")
    if data:
        return Experiment.parse_raw(data)
    return None


async def save_experiment(experiment: Experiment):
    """Save experiment to storage"""
    if redis_client:
        await redis_client.set(
            f"experiment:{experiment.id}", experiment.json(), ex=86400 * 30
        )


async def get_active_experiments() -> List[Experiment]:
    """Get all active experiments"""
    experiments = []

    if redis_client:
        keys = await redis_client.keys("experiment:*")
        for key in keys:
            data = await redis_client.get(key)
            if data:
                exp = Experiment.parse_raw(data)
                if exp.status == ExperimentStatus.RUNNING:
                    experiments.append(exp)

    return experiments


async def log_routing_decision(
    experiment_id: str, user_id: str, model: str, variant: str
):
    """Log routing decision for analysis"""
    if redis_client:
        key = f"routing:{experiment_id}:{datetime.utcnow().strftime('%Y%m%d')}"
        await redis_client.hincrby(key, f"{variant}:count", 1)
        await redis_client.expire(key, 86400 * 7)  # 7 days
