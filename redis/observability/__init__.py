"""
OpenTelemetry observability support for redis-py.

This module provides native OpenTelemetry instrumentation for Redis client operations,
including metrics, traces (future), and logs (future).

Phase 1 (Current): Metrics support
- Connection pool metrics
- Command execution metrics
- Cluster-specific metrics

Usage:
    Set up OpenTelemetry globally in your application:

    >>> from opentelemetry import metrics
    >>> from opentelemetry.sdk.metrics import MeterProvider
    >>> from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    >>> from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    >>>
    >>> # Create and configure MeterProvider
    >>> exporter = OTLPMetricExporter(endpoint="http://localhost:4318/v1/metrics")
    >>> reader = PeriodicExportingMetricReader(exporter=exporter)
    >>> provider = MeterProvider(metric_readers=[reader])
    >>> metrics.set_meter_provider(provider)

    Then initialize redis-py observability:

    >>> from redis.observability import get_observability_instance, OTelConfig
    >>>
    >>> otel = get_observability_instance()
    >>> otel.init(OTelConfig(enable_metrics=True))

    All Redis clients automatically collect metrics:

    >>> import redis
    >>> r = redis.Redis(host='localhost', port=6379)
    >>> r.set('key', 'value')  # Metrics collected automatically
"""

from redis.observability.attributes import AttributeBuilder
from redis.observability.config import (
    HistogramAggregation,
    MetricGroup,
    MetricsConfig,
    OTelConfig,
)
from redis.observability.metrics import RedisMetricsCollector
from redis.observability.providers import (
    ObservabilityInstance,
    OTelProviderManager,
    force_flush_metrics,
    get_observability_instance,
    get_provider_manager,
    init_observability,
    is_observability_enabled,
    shutdown_observability,
)
from redis.observability.recorder import (
    record_connection_create_time,
    record_operation_duration,
)
from redis.observability.timing import (
    ConnectionTimingContext,
    Timer,
    TimingContext,
)

__all__ = [
    # Configuration
    "OTelConfig",
    "MetricsConfig",
    "MetricGroup",
    "HistogramAggregation",
    # Advanced API (for more control)
    "get_observability_instance",
    "ObservabilityInstance",
    "shutdown_observability",
    "force_flush_metrics",
    "is_observability_enabled",
    "get_provider_manager",
    # Simple recording API (used by Redis core)
    "record_operation_duration",
    "record_connection_create_time",
    # Internal classes (for advanced usage)
    "AttributeBuilder",
    "ConnectionTimingContext",
    "RedisMetricsCollector",
    "OTelProviderManager",
    "Timer",
    "TimingContext",
]

