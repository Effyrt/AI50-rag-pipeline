"""
OpenTelemetry integration for distributed tracing and metrics.
"""
import time
import logging
from typing import Optional, Dict, Any, Callable
from functools import wraps
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class Telemetry:
    """
    Simple telemetry wrapper for tracking performance and errors.
    In production, replace with OpenTelemetry SDK.
    """
    
    def __init__(self):
        self.metrics: Dict[str, list] = {}
        self.enabled = True
    
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a metric value."""
        if not self.enabled:
            return
        
        if name not in self.metrics:
            self.metrics[name] = []
        
        self.metrics[name].append({
            "value": value,
            "timestamp": time.time(),
            "tags": tags or {}
        })
    
    def get_metrics(self, name: str) -> list:
        """Get all recorded values for a metric."""
        return self.metrics.get(name, [])
    
    def clear_metrics(self):
        """Clear all metrics."""
        self.metrics.clear()
    
    @contextmanager
    def track_duration(self, operation: str, tags: Optional[Dict[str, str]] = None):
        """Context manager to track operation duration."""
        start_time = time.time()
        error_occurred = False
        
        try:
            yield
        except Exception as e:
            error_occurred = True
            raise
        finally:
            duration = time.time() - start_time
            metric_tags = tags or {}
            metric_tags["status"] = "error" if error_occurred else "success"
            
            self.record_metric(f"{operation}_duration_seconds", duration, metric_tags)
            
            logger.info(
                f"Operation '{operation}' completed in {duration:.3f}s "
                f"(status: {metric_tags['status']})"
            )


# Global telemetry instance
telemetry = Telemetry()


def track_time(operation_name: str):
    """Decorator to track function execution time."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            with telemetry.track_duration(operation_name, {"function": func.__name__}):
                return func(*args, **kwargs)
        return wrapper
    return decorator