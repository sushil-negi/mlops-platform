"""
Prometheus metrics for Feature Store service
"""

import time
from functools import wraps
from typing import Callable, Dict, Optional

from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import structlog

logger = structlog.get_logger()


class FeatureStoreMetrics:
    """Prometheus metrics collector for Feature Store"""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        
        # Feature Store specific metrics
        self.requests_total = Counter(
            'feature_store_requests_total',
            'Total requests to Feature Store',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )
        
        self.request_duration = Histogram(
            'feature_store_request_duration_seconds',
            'Request duration in seconds',
            ['method', 'endpoint'],
            buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
            registry=self.registry
        )
        
        self.active_feature_sets = Gauge(
            'feature_store_active_feature_sets',
            'Number of active feature sets',
            registry=self.registry
        )
        
        self.total_features = Gauge(
            'feature_store_total_features',
            'Total number of features',
            registry=self.registry
        )
        
        self.feature_retrievals = Counter(
            'feature_store_feature_retrievals_total',
            'Total feature retrievals',
            ['feature_set', 'status'],
            registry=self.registry
        )
        
        self.feature_ingestion = Counter(
            'feature_store_feature_ingestion_total',
            'Total feature ingestion events',
            ['feature_set', 'status'],
            registry=self.registry
        )
        
        self.query_latency = Histogram(
            'feature_store_query_duration_seconds',
            'Feature query latency',
            ['query_type'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
            registry=self.registry
        )
        
        self.storage_operations = Counter(
            'feature_store_storage_operations_total',
            'Storage operations (DuckDB, S3)',
            ['operation', 'storage', 'status'],
            registry=self.registry
        )
        
        self.cache_operations = Counter(
            'feature_store_cache_operations_total',
            'Cache operations',
            ['operation', 'result'],
            registry=self.registry
        )
        
        # System metrics
        self.database_connections = Gauge(
            'feature_store_database_connections',
            'Active database connections',
            registry=self.registry
        )
        
        self.memory_usage = Gauge(
            'feature_store_memory_usage_bytes',
            'Memory usage in bytes',
            registry=self.registry
        )
    
    def track_request(self, method: str, endpoint: str, status_code: int):
        """Track HTTP request metrics"""
        self.requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=str(status_code)
        ).inc()
    
    def track_feature_retrieval(self, feature_set: str, success: bool):
        """Track feature retrieval operations"""
        status = 'success' if success else 'error'
        self.feature_retrievals.labels(
            feature_set=feature_set,
            status=status
        ).inc()
    
    def track_feature_ingestion(self, feature_set: str, success: bool):
        """Track feature ingestion operations"""
        status = 'success' if success else 'error'
        self.feature_ingestion.labels(
            feature_set=feature_set,
            status=status
        ).inc()
    
    def track_storage_operation(self, operation: str, storage: str, success: bool):
        """Track storage operations"""
        status = 'success' if success else 'error'
        self.storage_operations.labels(
            operation=operation,
            storage=storage,
            status=status
        ).inc()
    
    def track_cache_operation(self, operation: str, hit: bool):
        """Track cache operations"""
        result = 'hit' if hit else 'miss'
        self.cache_operations.labels(
            operation=operation,
            result=result
        ).inc()
    
    def update_feature_sets_count(self, count: int):
        """Update active feature sets count"""
        self.active_feature_sets.set(count)
    
    def update_features_count(self, count: int):
        """Update total features count"""
        self.total_features.set(count)
    
    def record_query_duration(self, query_type: str, duration: float):
        """Record query duration"""
        self.query_latency.labels(query_type=query_type).observe(duration)
    
    def get_metrics(self) -> str:
        """Get metrics in Prometheus format"""
        return generate_latest(self.registry).decode('utf-8')


# Global metrics instance
feature_store_metrics = FeatureStoreMetrics()


def track_endpoint_metrics(endpoint_name: str):
    """Decorator to track endpoint metrics"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                # Track successful request
                duration = time.time() - start_time
                feature_store_metrics.request_duration.labels(
                    method='GET',  # Assume GET for simplicity
                    endpoint=endpoint_name
                ).observe(duration)
                
                feature_store_metrics.track_request('GET', endpoint_name, 200)
                
                return result
                
            except Exception as e:
                # Track failed request
                duration = time.time() - start_time
                feature_store_metrics.request_duration.labels(
                    method='GET',
                    endpoint=endpoint_name
                ).observe(duration)
                
                feature_store_metrics.track_request('GET', endpoint_name, 500)
                raise
                
        return wrapper
    return decorator


def create_metrics_response() -> Response:
    """Create HTTP response with Prometheus metrics"""
    metrics_data = feature_store_metrics.get_metrics()
    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST
    )