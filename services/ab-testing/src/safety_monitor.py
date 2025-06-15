"""
Safety monitoring for A/B tests
Ensures healthcare safety thresholds are maintained
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List

import httpx
import structlog

try:
    from .models import SafetyThresholds, SafetyViolation
except ImportError:
    from models import SafetyThresholds, SafetyViolation

logger = structlog.get_logger()


class SafetyMonitor:
    """Monitors A/B tests for healthcare safety violations"""

    def __init__(self, prometheus_url: str, alertmanager_url: str):
        self.prometheus_url = prometheus_url
        self.alertmanager_url = alertmanager_url
        self.violations: Dict[str, List[SafetyViolation]] = {}

    async def check_experiment_safety(self, experiment_id: str) -> bool:
        """Check if experiment is meeting safety thresholds"""
        try:
            # Get current metrics from Prometheus
            metrics = await self._query_prometheus_metrics(experiment_id)

            if not metrics:
                logger.warning(
                    "No metrics available for safety check", experiment_id=experiment_id
                )
                return True  # Allow experiment to continue if no metrics yet

            # Get safety thresholds for this experiment
            thresholds = await self._get_experiment_thresholds(experiment_id)

            violations = []

            # Check each model's metrics
            for model in ["a", "b"]:
                model_metrics = metrics.get(f"model_{model}", {})

                # Crisis detection rate check (CRITICAL)
                crisis_rate = model_metrics.get("crisis_detection_rate")
                if (
                    crisis_rate is not None
                    and crisis_rate < thresholds.crisis_detection_rate
                ):
                    violations.append(
                        SafetyViolation(
                            timestamp=datetime.utcnow(),
                            experiment_id=experiment_id,
                            metric="crisis_detection_rate",
                            threshold=thresholds.crisis_detection_rate,
                            actual_value=crisis_rate,
                            model=model,
                            severity="critical",
                            action_taken="emergency_stop",
                        )
                    )

                # Empathy score check
                empathy_score = model_metrics.get("empathy_score")
                if (
                    empathy_score is not None
                    and empathy_score < thresholds.empathy_score
                ):
                    violations.append(
                        SafetyViolation(
                            timestamp=datetime.utcnow(),
                            experiment_id=experiment_id,
                            metric="empathy_score",
                            threshold=thresholds.empathy_score,
                            actual_value=empathy_score,
                            model=model,
                            severity="warning",
                        )
                    )

                # Accuracy check
                accuracy = model_metrics.get("accuracy")
                if accuracy is not None and accuracy < thresholds.accuracy:
                    violations.append(
                        SafetyViolation(
                            timestamp=datetime.utcnow(),
                            experiment_id=experiment_id,
                            metric="accuracy",
                            threshold=thresholds.accuracy,
                            actual_value=accuracy,
                            model=model,
                            severity="warning",
                        )
                    )

                # Response time check
                response_time_95th = model_metrics.get("response_time_p95")
                if (
                    response_time_95th is not None
                    and response_time_95th > thresholds.response_time_95th
                ):
                    violations.append(
                        SafetyViolation(
                            timestamp=datetime.utcnow(),
                            experiment_id=experiment_id,
                            metric="response_time_95th",
                            threshold=thresholds.response_time_95th,
                            actual_value=response_time_95th,
                            model=model,
                            severity="warning",
                        )
                    )

            # Store violations
            if violations:
                if experiment_id not in self.violations:
                    self.violations[experiment_id] = []
                self.violations[experiment_id].extend(violations)

                # Log violations
                for violation in violations:
                    logger.warning(
                        "Safety violation detected",
                        experiment_id=experiment_id,
                        metric=violation.metric,
                        threshold=violation.threshold,
                        actual_value=violation.actual_value,
                        model=violation.model,
                        severity=violation.severity,
                    )

                # Send alerts for critical violations
                critical_violations = [
                    v for v in violations if v.severity == "critical"
                ]
                if critical_violations:
                    await self._send_critical_alert(experiment_id, critical_violations)
                    return False  # Critical violation - experiment should stop

            return True  # All safety checks passed

        except Exception as e:
            logger.error(
                "Error in safety check", experiment_id=experiment_id, error=str(e)
            )
            return False  # Fail safe - stop experiment on error

    async def start_monitoring(self, experiment_id: str):
        """Start continuous monitoring for an experiment"""
        logger.info("Starting safety monitoring", experiment_id=experiment_id)

        while True:
            try:
                is_safe = await self.check_experiment_safety(experiment_id)

                if not is_safe:
                    logger.critical(
                        "Safety violation - monitoring stopped",
                        experiment_id=experiment_id,
                    )
                    break

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(
                    "Error in monitoring loop",
                    experiment_id=experiment_id,
                    error=str(e),
                )
                await asyncio.sleep(60)  # Wait longer on error

    async def get_safety_status(self, experiment_id: str) -> Dict:
        """Get current safety status for an experiment"""
        recent_violations = []

        if experiment_id in self.violations:
            # Get violations from last hour
            cutoff = datetime.utcnow() - timedelta(hours=1)
            recent_violations = [
                v for v in self.violations[experiment_id] if v.timestamp > cutoff
            ]

        return {
            "is_safe": len([v for v in recent_violations if v.severity == "critical"])
            == 0,
            "recent_violations": len(recent_violations),
            "last_check": datetime.utcnow().isoformat(),
            "violations": [v.dict() for v in recent_violations],
        }

    async def _query_prometheus_metrics(self, experiment_id: str) -> Dict:
        """Query Prometheus for experiment metrics"""
        try:
            async with httpx.AsyncClient() as client:
                metrics = {}

                # Define queries for each metric
                queries = {
                    "model_a_accuracy": (
                        f"avg(healthcare_ai_model_accuracy{{"
                        f'experiment_id="{experiment_id}",variant="control"}})'
                    ),
                    "model_b_accuracy": (
                        f"avg(healthcare_ai_model_accuracy{{"
                        f'experiment_id="{experiment_id}",variant="treatment"}})'
                    ),
                    "model_a_crisis_rate": (
                        f"avg(healthcare_ai_crisis_detection_rate{{"
                        f'experiment_id="{experiment_id}",variant="control"}})'
                    ),
                    "model_b_crisis_rate": (
                        f"avg(healthcare_ai_crisis_detection_rate{{"
                        f'experiment_id="{experiment_id}",variant="treatment"}})'
                    ),
                    "model_a_empathy": (
                        f"avg(healthcare_ai_empathy_score{{"
                        f'experiment_id="{experiment_id}",variant="control"}})'
                    ),
                    "model_b_empathy": (
                        f"avg(healthcare_ai_empathy_score{{"
                        f'experiment_id="{experiment_id}",variant="treatment"}})'
                    ),
                    "model_a_response_time_p95": (
                        f"histogram_quantile(0.95, rate("
                        f"healthcare_ai_response_time_seconds_bucket{{"
                        f'experiment_id="{experiment_id}",variant="control"}}[5m]))'
                    ),
                    "model_b_response_time_p95": (
                        f"histogram_quantile(0.95, rate("
                        f"healthcare_ai_response_time_seconds_bucket{{"
                        f'experiment_id="{experiment_id}",variant="treatment"}}[5m]))'
                    ),
                }

                for metric_name, query in queries.items():
                    response = await client.get(
                        f"{self.prometheus_url}/api/v1/query", params={"query": query}
                    )

                    if response.status_code == 200:
                        data = response.json()

                        if data["status"] == "success" and data["data"]["result"]:
                            value = float(data["data"]["result"][0]["value"][1])

                            # Parse metric name to determine model and metric type
                            if "model_a" in metric_name:
                                model = "model_a"
                            else:
                                model = "model_b"

                            if model not in metrics:
                                metrics[model] = {}

                            if "accuracy" in metric_name:
                                metrics[model]["accuracy"] = value
                            elif "crisis_rate" in metric_name:
                                metrics[model]["crisis_detection_rate"] = value
                            elif "empathy" in metric_name:
                                metrics[model]["empathy_score"] = value
                            elif "response_time_p95" in metric_name:
                                metrics[model]["response_time_p95"] = value

                return metrics

        except Exception as e:
            logger.error("Failed to query Prometheus", error=str(e))
            return {}

    async def _get_experiment_thresholds(self, experiment_id: str) -> SafetyThresholds:
        """Get safety thresholds for an experiment"""
        # TODO: Get from experiment configuration
        # For now, use default thresholds
        return SafetyThresholds()

    async def _send_critical_alert(
        self, experiment_id: str, violations: List[SafetyViolation]
    ):
        """Send critical alert for safety violations"""
        try:
            alert_data = {
                "receiver": "ab-test-safety",
                "status": "firing",
                "alerts": [
                    {
                        "status": "firing",
                        "labels": {
                            "alertname": "ABTestSafetyViolation",
                            "severity": "critical",
                            "experiment_id": experiment_id,
                            "action": "stop_experiment",
                        },
                        "annotations": {
                            "summary": (
                                f"Safety violation in experiment {experiment_id}"
                            ),
                            "description": (
                                f"Critical safety thresholds violated: "
                                f"{', '.join([v.metric for v in violations])}"
                            ),
                            "violations": json.dumps([v.dict() for v in violations]),
                        },
                        "startsAt": datetime.utcnow().isoformat(),
                        "generatorURL": (
                            f"http://ab-testing:8000/experiments/{experiment_id}/safety"
                        ),
                    }
                ],
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.alertmanager_url}/api/v1/alerts", json=alert_data
                )

                if response.status_code == 200:
                    logger.info("Critical alert sent", experiment_id=experiment_id)
                else:
                    logger.error(
                        "Failed to send alert", status_code=response.status_code
                    )

        except Exception as e:
            logger.error("Failed to send critical alert", error=str(e))
