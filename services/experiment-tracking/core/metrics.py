"""
Prometheus metrics for Experiment Tracking service
"""

from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response


class ExperimentTrackingMetrics:
    """Prometheus metrics collector for Experiment Tracking"""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        
        # Experiment Tracking specific metrics
        self.requests_total = Counter(
            'experiment_tracking_requests_total',
            'Total requests to Experiment Tracking',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )
        
        self.request_duration = Histogram(
            'experiment_tracking_request_duration_seconds',
            'Request duration in seconds',
            ['method', 'endpoint'],
            buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
            registry=self.registry
        )
        
        self.active_experiments = Gauge(
            'experiment_tracking_active_experiments',
            'Number of active experiments',
            registry=self.registry
        )
        
        self.total_runs = Gauge(
            'experiment_tracking_total_runs',
            'Total number of experiment runs',
            registry=self.registry
        )
        
        self.runs_created = Counter(
            'experiment_tracking_runs_created_total',
            'Total experiment runs created',
            ['experiment_id', 'status'],
            registry=self.registry
        )
        
        self.metrics_logged = Counter(
            'experiment_tracking_metrics_logged_total',
            'Total metrics logged',
            ['experiment_id', 'metric_type'],
            registry=self.registry
        )
        
        self.artifacts_stored = Counter(
            'experiment_tracking_artifacts_stored_total',
            'Total artifacts stored',
            ['experiment_id', 'artifact_type'],
            registry=self.registry
        )
    
    def get_metrics(self) -> str:
        """Get metrics in Prometheus format"""
        return generate_latest(self.registry).decode('utf-8')


# Global metrics instance
experiment_tracking_metrics = ExperimentTrackingMetrics()


def create_metrics_response() -> Response:
    """Create HTTP response with Prometheus metrics"""
    metrics_data = experiment_tracking_metrics.get_metrics()
    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST
    )