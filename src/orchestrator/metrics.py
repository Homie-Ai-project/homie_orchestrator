"""
Metrics and monitoring for Homie Orchestrator

Provides Prometheus-style metrics for monitoring the orchestrator.
"""

import time
from typing import Dict, Any
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import FastAPI, Response


# Metrics
container_operations_total = Counter(
    'orchestrator_container_operations_total',
    'Total number of container operations',
    ['operation', 'service', 'status']
)

containers_managed_total = Gauge(
    'orchestrator_containers_managed_total',
    'Total number of managed containers'
)

container_status_gauge = Gauge(
    'orchestrator_container_status',
    'Container status (1=running, 0=stopped, -1=error)',
    ['service']
)

health_check_status = Gauge(
    'orchestrator_health_check_status',
    'Health check status (1=healthy, 0=unhealthy)',
    ['service']
)

backup_operations_total = Counter(
    'orchestrator_backup_operations_total',
    'Total number of backup operations',
    ['operation', 'status']
)

api_requests_total = Counter(
    'orchestrator_api_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'status']
)

api_request_duration = Histogram(
    'orchestrator_api_request_duration_seconds',
    'API request duration in seconds',
    ['method', 'endpoint']
)

system_uptime = Gauge(
    'orchestrator_uptime_seconds',
    'Orchestrator uptime in seconds'
)

# Start time for uptime calculation
START_TIME = time.time()


def setup_metrics(app: FastAPI, metrics_port: int = 9090):
    """Setup metrics endpoint"""
    
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint"""
        # Update uptime
        system_uptime.set(time.time() - START_TIME)
        
        # Generate metrics
        metrics_output = generate_latest()
        return Response(content=metrics_output, media_type=CONTENT_TYPE_LATEST)


def record_container_operation(operation: str, service: str, status: str):
    """Record a container operation"""
    container_operations_total.labels(
        operation=operation,
        service=service,
        status=status
    ).inc()


def update_containers_managed(count: int):
    """Update the number of managed containers"""
    containers_managed_total.set(count)


def update_container_status(service: str, status: str):
    """Update container status metric"""
    status_value = {
        "running": 1,
        "stopped": 0,
        "error": -1,
        "unknown": -2
    }.get(status, -2)
    
    container_status_gauge.labels(service=service).set(status_value)


def update_health_check_status(service: str, healthy: bool):
    """Update health check status metric"""
    health_check_status.labels(service=service).set(1 if healthy else 0)


def record_backup_operation(operation: str, status: str):
    """Record a backup operation"""
    backup_operations_total.labels(
        operation=operation,
        status=status
    ).inc()


def record_api_request(method: str, endpoint: str, status_code: int, duration: float):
    """Record API request metrics"""
    api_requests_total.labels(
        method=method,
        endpoint=endpoint,
        status=str(status_code)
    ).inc()
    
    api_request_duration.labels(
        method=method,
        endpoint=endpoint
    ).observe(duration)


class MetricsMiddleware:
    """Middleware to collect API metrics"""
    
    def __init__(self, app: FastAPI):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        start_time = time.time()
        method = scope["method"]
        path = scope["path"]
        
        # Simplify path for metrics (remove IDs)
        endpoint = self._normalize_endpoint(path)
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code = message["status"]
                duration = time.time() - start_time
                
                # Record metrics
                record_api_request(method, endpoint, status_code, duration)
            
            await send(message)
        
        await self.app(scope, receive, send_wrapper)
    
    def _normalize_endpoint(self, path: str) -> str:
        """Normalize endpoint path for metrics"""
        # Replace UUIDs and IDs with placeholders
        import re
        
        # Replace container/service names with placeholder
        path = re.sub(r'/containers/[^/]+', '/containers/{service}', path)
        path = re.sub(r'/services/[^/]+', '/services/{service}', path)
        
        # Replace UUIDs with placeholder
        path = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '/{uuid}',
            path
        )
        
        return path
