"""
Simple, clean API for recording observability metrics.

This module provides a straightforward interface for Redis core code to record
metrics without needing to know about OpenTelemetry internals.

Usage in Redis core code:
    from redis.observability.recorder import record_operation_duration
    
    start_time = time.monotonic()
    # ... execute Redis command ...
    record_operation_duration(
        command_name='SET',
        duration_seconds=time.monotonic() - start_time,
        server_address='localhost',
        server_port=6379,
        db_namespace='0',
        error=None
    )
"""

import time
from typing import Optional


# Global metrics collector instance (lazy-initialized)
_metrics_collector: Optional[object] = None


def record_operation_duration(
    command_name: str,
    duration_seconds: float,
    server_address: Optional[str] = None,
    server_port: Optional[int] = None,
    db_namespace: Optional[str] = None,
    error: Optional[Exception] = None,
) -> None:
    """
    Record a Redis command execution duration.
    
    This is a simple, clean API that Redis core code can call directly.
    If observability is not enabled, this returns immediately with zero overhead.
    
    Args:
        command_name: Redis command name (e.g., 'GET', 'SET')
        duration_seconds: Command execution time in seconds
        server_address: Redis server address
        server_port: Redis server port
        db_namespace: Redis database index
        error: Exception if command failed, None if successful
    
    Example:
        >>> start = time.monotonic()
        >>> # ... execute command ...
        >>> record_operation_duration('SET', time.monotonic() - start, 'localhost', 6379, '0')
    """
    global _metrics_collector
    
    # Fast path: if collector not initialized, observability is disabled
    if _metrics_collector is None:
        # Try to initialize (only once)
        _metrics_collector = _get_or_create_collector()
        if _metrics_collector is None:
            return  # Observability not enabled
    
    # Determine error type and status
    error_type = None
    status_code = "ok"
    if error is not None:
        error_type = type(error).__name__
        status_code = "error"
    
    # Record the metric
    try:
        _metrics_collector.record_operation_duration(
            command_name=command_name,
            duration_seconds=duration_seconds,
            server_address=server_address,
            server_port=server_port,
            db_namespace=db_namespace,
            error_type=error_type,
            response_status_code=status_code,
            network_peer_address=server_address,
            network_peer_port=server_port,
        )
    except Exception:
        # Don't let metric recording errors break Redis operations
        pass


def record_connection_create_time(
    pool_name: str,
    duration_seconds: float,
) -> None:
    """
    Record connection creation time.
    
    Args:
        pool_name: Connection pool identifier
        duration_seconds: Time taken to create connection in seconds
    
    Example:
        >>> start = time.monotonic()
        >>> # ... create connection ...
        >>> record_connection_create_time('ConnectionPool<localhost:6379>', time.monotonic() - start)
    """
    global _metrics_collector
    
    # Fast path: if collector not initialized, observability is disabled
    if _metrics_collector is None:
        _metrics_collector = _get_or_create_collector()
        if _metrics_collector is None:
            return
    
    try:
        _metrics_collector.record_connection_create_time(
            pool_name=pool_name,
            duration_seconds=duration_seconds,
        )
    except Exception:
        pass


def _get_or_create_collector() -> Optional[object]:
    """
    Get or create the global metrics collector.
    
    Returns:
        RedisMetricsCollector instance if observability is enabled, None otherwise
    """
    try:
        from redis.observability.providers import get_provider_manager
        from redis.observability.metrics import RedisMetricsCollector
        
        manager = get_provider_manager()
        if manager is None or not manager.config.enable_metrics:
            return None
        
        # Get meter from the global MeterProvider
        meter = manager.get_meter_provider().get_meter(
            RedisMetricsCollector.METER_NAME,
            RedisMetricsCollector.METER_VERSION
        )
        
        return RedisMetricsCollector(meter, manager.config)
    
    except ImportError:
        # Observability module not available
        return None
    except Exception:
        # Any other error - don't break Redis operations
        return None


def reset_collector() -> None:
    """
    Reset the global collector (used for testing or re-initialization).
    """
    global _metrics_collector
    _metrics_collector = None


def is_enabled() -> bool:
    """
    Check if observability is enabled.
    
    Returns:
        True if metrics are being collected, False otherwise
    """
    global _metrics_collector
    
    if _metrics_collector is None:
        _metrics_collector = _get_or_create_collector()
    
    return _metrics_collector is not None

