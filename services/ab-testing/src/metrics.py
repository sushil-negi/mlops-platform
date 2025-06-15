"""
Metrics collection and aggregation for A/B testing experiments
"""

from datetime import datetime, timedelta
from typing import Dict, Optional

import httpx
import redis.asyncio as redis
import structlog
from prometheus_client import CollectorRegistry, Counter, Histogram

try:
    from .models import MetricSnapshot
except ImportError:
    from models import MetricSnapshot

logger = structlog.get_logger()


class ExperimentMetrics:
    """Collects and aggregates metrics for A/B testing experiments"""

    def __init__(self, registry: CollectorRegistry):
        self.registry = registry
        self.redis_client: Optional[redis.Redis] = None

        # Prometheus metrics for A/B testing
        self.experiment_accuracy = Histogram(
            "ab_test_model_accuracy",
            "Model accuracy in A/B tests",
            ["experiment_id", "model"],
            registry=registry,
        )

        self.experiment_empathy = Histogram(
            "ab_test_empathy_score",
            "Empathy score in A/B tests",
            ["experiment_id", "model"],
            registry=registry,
        )

        self.experiment_response_time = Histogram(
            "ab_test_response_time_seconds",
            "Response time in A/B tests",
            ["experiment_id", "model"],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=registry,
        )

        self.experiment_crisis_detection = Histogram(
            "ab_test_crisis_detection_rate",
            "Crisis detection rate in A/B tests",
            ["experiment_id", "model"],
            registry=registry,
        )

        self.experiment_requests = Counter(
            "ab_test_requests_total",
            "Total requests per model in A/B tests",
            ["experiment_id", "model"],
            registry=registry,
        )

        self.experiment_errors = Counter(
            "ab_test_errors_total",
            "Total errors per model in A/B tests",
            ["experiment_id", "model", "error_type"],
            registry=registry,
        )

    async def set_redis_client(self, redis_client: redis.Redis):
        """Set Redis client for persistent storage"""
        self.redis_client = redis_client

    async def log_metrics(self, experiment_id: str, metrics: Dict):
        """Log metrics for an experiment"""
        try:
            timestamp = datetime.utcnow()

            # Expected metrics format:
            # {
            #   "model": "model_a" or "model_b",
            #   "accuracy": 0.95,
            #   "empathy_score": 0.78,
            #   "response_time": 0.34,
            #   "crisis_detection_rate": 0.99,
            #   "error_occurred": false,
            #   "error_type": "timeout" (if error_occurred is true)
            # }

            model = metrics.get("model", "unknown")
            variant = "control" if model.endswith("_a") else "treatment"

            # Update Prometheus metrics
            if "accuracy" in metrics:
                self.experiment_accuracy.labels(
                    experiment_id=experiment_id, model=variant
                ).observe(metrics["accuracy"])

            if "empathy_score" in metrics:
                self.experiment_empathy.labels(
                    experiment_id=experiment_id, model=variant
                ).observe(metrics["empathy_score"])

            if "response_time" in metrics:
                self.experiment_response_time.labels(
                    experiment_id=experiment_id, model=variant
                ).observe(metrics["response_time"])

            if "crisis_detection_rate" in metrics:
                self.experiment_crisis_detection.labels(
                    experiment_id=experiment_id, model=variant
                ).observe(metrics["crisis_detection_rate"])

            # Count requests
            self.experiment_requests.labels(
                experiment_id=experiment_id, model=variant
            ).inc()

            # Count errors
            if metrics.get("error_occurred", False):
                error_type = metrics.get("error_type", "unknown")
                self.experiment_errors.labels(
                    experiment_id=experiment_id, model=variant, error_type=error_type
                ).inc()

            # Store detailed metrics in Redis for analysis
            if self.redis_client:
                snapshot = MetricSnapshot(
                    timestamp=timestamp,
                    model=model,
                    accuracy=metrics.get("accuracy"),
                    empathy_score=metrics.get("empathy_score"),
                    response_time_p50=metrics.get(
                        "response_time"
                    ),  # Individual response time
                    crisis_detection_rate=metrics.get("crisis_detection_rate"),
                    error_rate=1.0 if metrics.get("error_occurred") else 0.0,
                    sample_count=1,
                )

                # Store as time series data
                key = (
                    f"metrics:{experiment_id}:{model}:{timestamp.strftime('%Y%m%d%H')}"
                )
                await self.redis_client.lpush(key, snapshot.json())
                await self.redis_client.expire(key, 86400 * 7)  # 7 days retention

            logger.debug(
                "Metrics logged",
                experiment_id=experiment_id,
                model=model,
                metrics=metrics,
            )

        except Exception as e:
            logger.error(
                "Failed to log metrics", experiment_id=experiment_id, error=str(e)
            )
            raise

    async def get_experiment_metrics(
        self, experiment_id: str, hours_back: int = 24
    ) -> Dict:
        """Get aggregated metrics for an experiment"""
        try:
            if not self.redis_client:
                return {"error": "Redis not available"}

            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)

            # Get raw metrics from Redis
            metrics_data = {
                "model_a": {
                    "samples": [],
                    "accuracy": [],
                    "empathy_score": [],
                    "response_time": [],
                    "crisis_detection_rate": [],
                },
                "model_b": {
                    "samples": [],
                    "accuracy": [],
                    "empathy_score": [],
                    "response_time": [],
                    "crisis_detection_rate": [],
                },
            }

            # Search for metric keys
            pattern = f"metrics:{experiment_id}:*"
            keys = await self.redis_client.keys(pattern)

            for key in keys:
                # Get all metrics for this key
                raw_metrics = await self.redis_client.lrange(key, 0, -1)

                for raw_metric in raw_metrics:
                    try:
                        snapshot = MetricSnapshot.parse_raw(raw_metric)

                        # Filter by time
                        if snapshot.timestamp < cutoff_time:
                            continue

                        # Determine model group
                        model_key = (
                            "model_a" if snapshot.model.endswith("_a") else "model_b"
                        )

                        # Add to aggregated data
                        metrics_data[model_key]["samples"].append(snapshot.dict())

                        if snapshot.accuracy is not None:
                            metrics_data[model_key]["accuracy"].append(
                                snapshot.accuracy
                            )

                        if snapshot.empathy_score is not None:
                            metrics_data[model_key]["empathy_score"].append(
                                snapshot.empathy_score
                            )

                        if snapshot.response_time_p50 is not None:
                            metrics_data[model_key]["response_time"].append(
                                snapshot.response_time_p50
                            )

                        if snapshot.crisis_detection_rate is not None:
                            metrics_data[model_key]["crisis_detection_rate"].append(
                                snapshot.crisis_detection_rate
                            )

                    except Exception as e:
                        logger.warning("Failed to parse metric snapshot", error=str(e))
                        continue

            # Add summary statistics
            for model in ["model_a", "model_b"]:
                data = metrics_data[model]
                data["sample_count"] = len(data["samples"])

                for metric in [
                    "accuracy",
                    "empathy_score",
                    "response_time",
                    "crisis_detection_rate",
                ]:
                    values = data[metric]
                    if values:
                        data[f"{metric}_mean"] = sum(values) / len(values)
                        data[f"{metric}_count"] = len(values)
                    else:
                        data[f"{metric}_mean"] = 0
                        data[f"{metric}_count"] = 0

            return metrics_data

        except Exception as e:
            logger.error(
                "Failed to get experiment metrics",
                experiment_id=experiment_id,
                error=str(e),
            )
            return {"error": str(e)}

    async def get_real_time_metrics(self, experiment_id: str) -> Dict:
        """Get real-time metrics from Prometheus"""
        try:
            prometheus_url = "http://localhost:9090"  # TODO: Make configurable

            async with httpx.AsyncClient() as client:
                metrics = {}

                # Define queries for real-time metrics
                queries = {
                    "requests_per_second_a": (
                        f"rate(ab_test_requests_total{{"
                        f'experiment_id="{experiment_id}",model="control"}}[1m])'
                    ),
                    "requests_per_second_b": (
                        f"rate(ab_test_requests_total{{"
                        f'experiment_id="{experiment_id}",model="treatment"}}[1m])'
                    ),
                    "error_rate_a": (
                        f"rate(ab_test_errors_total{{"
                        f'experiment_id="{experiment_id}",model="control"}}[5m])'
                    ),
                    "error_rate_b": (
                        f"rate(ab_test_errors_total{{"
                        f'experiment_id="{experiment_id}",model="treatment"}}[5m])'
                    ),
                    "avg_response_time_a": (
                        f"rate(ab_test_response_time_seconds_sum{{"
                        f'experiment_id="{experiment_id}",model="control"}}[5m]) / '
                        f"rate(ab_test_response_time_seconds_count{{"
                        f'experiment_id="{experiment_id}",model="control"}}[5m])'
                    ),
                    "avg_response_time_b": (
                        f"rate(ab_test_response_time_seconds_sum{{"
                        f'experiment_id="{experiment_id}",model="treatment"}}[5m]) / '
                        f"rate(ab_test_response_time_seconds_count{{"
                        f'experiment_id="{experiment_id}",model="treatment"}}[5m])'
                    ),
                }

                for metric_name, query in queries.items():
                    try:
                        response = await client.get(
                            f"{prometheus_url}/api/v1/query",
                            params={"query": query},
                            timeout=5.0,
                        )

                        if response.status_code == 200:
                            data = response.json()
                            if data["status"] == "success" and data["data"]["result"]:
                                value = float(data["data"]["result"][0]["value"][1])
                                metrics[metric_name] = value
                            else:
                                metrics[metric_name] = 0.0
                        else:
                            metrics[metric_name] = 0.0

                    except Exception as e:
                        logger.warning(f"Failed to get {metric_name}", error=str(e))
                        metrics[metric_name] = 0.0

                return {
                    "model_a": {
                        "requests_per_second": metrics.get("requests_per_second_a", 0),
                        "error_rate": metrics.get("error_rate_a", 0),
                        "avg_response_time": metrics.get("avg_response_time_a", 0),
                    },
                    "model_b": {
                        "requests_per_second": metrics.get("requests_per_second_b", 0),
                        "error_rate": metrics.get("error_rate_b", 0),
                        "avg_response_time": metrics.get("avg_response_time_b", 0),
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                }

        except Exception as e:
            logger.error("Failed to get real-time metrics", error=str(e))
            return {"error": str(e)}

    async def calculate_statistical_readiness(self, experiment_id: str) -> Dict:
        """Calculate if experiment has enough data for statistical analysis"""
        try:
            metrics = await self.get_experiment_metrics(experiment_id)

            model_a_samples = len(metrics.get("model_a", {}).get("samples", []))
            model_b_samples = len(metrics.get("model_b", {}).get("samples", []))

            min_samples_needed = 30  # Minimum for t-test
            recommended_samples = 100  # For better power

            return {
                "model_a_samples": model_a_samples,
                "model_b_samples": model_b_samples,
                "min_samples_needed": min_samples_needed,
                "recommended_samples": recommended_samples,
                "ready_for_analysis": model_a_samples >= min_samples_needed
                and model_b_samples >= min_samples_needed,
                "has_recommended_power": model_a_samples >= recommended_samples
                and model_b_samples >= recommended_samples,
                "completion_percentage": min(
                    (model_a_samples + model_b_samples) / (2 * recommended_samples), 1.0
                )
                * 100,
            }

        except Exception as e:
            logger.error("Failed to calculate statistical readiness", error=str(e))
            return {"error": str(e)}
