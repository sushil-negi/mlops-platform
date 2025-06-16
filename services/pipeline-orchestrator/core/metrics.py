"""
Prometheus metrics for Pipeline Orchestrator service
"""

from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response


class PipelineOrchestratorMetrics:
    """Prometheus metrics collector for Pipeline Orchestrator"""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        
        # Pipeline Orchestrator specific metrics
        self.requests_total = Counter(
            'pipeline_orchestrator_requests_total',
            'Total requests to Pipeline Orchestrator',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )
        
        self.request_duration = Histogram(
            'pipeline_orchestrator_request_duration_seconds',
            'Request duration in seconds',
            ['method', 'endpoint'],
            buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
            registry=self.registry
        )
        
        self.active_pipelines = Gauge(
            'pipeline_orchestrator_active_pipelines',
            'Number of active pipelines',
            registry=self.registry
        )
        
        self.total_executions = Counter(
            'pipeline_orchestrator_executions_total',
            'Total pipeline executions',
            ['pipeline_id', 'status'],
            registry=self.registry
        )
        
        self.execution_duration = Histogram(
            'pipeline_orchestrator_execution_duration_seconds',
            'Pipeline execution duration',
            ['pipeline_id'],
            buckets=[1, 5, 10, 30, 60, 300, 600, 1800, 3600],
            registry=self.registry
        )
        
        self.task_executions = Counter(
            'pipeline_orchestrator_task_executions_total',
            'Total task executions',
            ['pipeline_id', 'task_type', 'status'],
            registry=self.registry
        )
        
        self.resource_usage = Histogram(
            'pipeline_orchestrator_resource_usage',
            'Resource usage during execution',
            ['resource_type', 'pipeline_id'],
            registry=self.registry
        )
        
        self.queue_size = Gauge(
            'pipeline_orchestrator_queue_size',
            'Current queue size',
            ['queue_type'],
            registry=self.registry
        )
    
    def get_metrics(self) -> str:
        """Get metrics in Prometheus format"""
        return generate_latest(self.registry).decode('utf-8')


# Global metrics instance
pipeline_orchestrator_metrics = PipelineOrchestratorMetrics()


def create_metrics_response() -> Response:
    """Create HTTP response with Prometheus metrics"""
    metrics_data = pipeline_orchestrator_metrics.get_metrics()
    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST
    )