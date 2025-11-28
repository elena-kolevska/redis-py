"""
OpenTelemetry configuration for redis-py.

This module handles configuration for OTel observability features,
including parsing environment variables and validating settings.
"""

from enum import Enum
from typing import List, Optional


class MetricGroup(str, Enum):
    """Metric groups that can be enabled/disabled."""
    RESILIENCY = "resiliency"
    CONNECTION_BASIC = "connection-basic"
    CONNECTION_ADVANCED = "connection-advanced"
    COMMAND = "command"
    CSC = "client-side-caching"
    STREAMING = "streaming"
    PUBSUB = "pubsub"


class HistogramAggregation(str, Enum):
    """Histogram aggregation modes."""
    EXPLICIT_BUCKET_HISTOGRAM = "explicit_bucket_histogram"
    BASE2_EXPONENTIAL_BUCKET_HISTOGRAM = "base2_exponential_bucket_histogram"


class MetricsConfig:
    """
    Configuration for Redis metrics collection.

    This class groups all metrics-related configuration options together.
    """
    DEFAULT_METRIC_GROUPS = [
        MetricGroup.CONNECTION_BASIC,
        MetricGroup.RESILIENCY,
    ]

    # Default bucket boundaries (in seconds)
    DEFAULT_BUCKETS_OPERATION_DURATION = [
        0.0001, 0.00025, 0.0005, 0.001, 0.0025, 0.005,
        0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5
    ]

    DEFAULT_BUCKETS_CONNECTION_CREATE_TIME = [
        0.0001, 0.00025, 0.0005, 0.001, 0.0025, 0.005,
        0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10
    ]

    DEFAULT_BUCKETS_CONNECTION_WAIT_TIME = [
        0.0001, 0.00025, 0.0005, 0.001, 0.0025, 0.005,
        0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10
    ]

    DEFAULT_BUCKETS_CONNECTION_USE_TIME = [
        0.0001, 0.00025, 0.0005, 0.001, 0.0025, 0.005,
        0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10
    ]

    DEFAULT_BUCKETS_STREAM_PROCESSING_DURATION = [
        0.0001, 0.00025, 0.0005, 0.001, 0.0025, 0.005,
        0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10
    ]

    def __init__(
        self,
        # Core enablement
        enabled: bool = False,
        enabled_metric_groups: Optional[List[MetricGroup]] = None,
        # Command filtering
        include_commands: Optional[List[str]] = None,
        exclude_commands: Optional[List[str]] = None,
        # Cardinality reduction
        hide_pubsub_channel_names: bool = False,
        hide_stream_names: bool = False,
        # Histogram configuration
        hist_aggregation: str = HistogramAggregation.EXPLICIT_BUCKET_HISTOGRAM,
        buckets_operation_duration: Optional[List[float]] = None,
        buckets_stream_processing_duration: Optional[List[float]] = None,
        buckets_connection_create_time: Optional[List[float]] = None,
        buckets_connection_wait_time: Optional[List[float]] = None,
        buckets_connection_use_time: Optional[List[float]] = None,
    ):
        """
        Initialize metrics configuration.

        Args:
            enabled: Enable/disable metrics emission (default: False)
            enabled_metric_groups: Metric groups to register (default: ["command", "connection-basic", "resiliency"])
            include_commands: Command allow-list for metrics (e.g., ["GET", "SET"])
            exclude_commands: Command deny-list for metrics
            hide_pubsub_channel_names: If True, omit channel label from Pub/Sub metrics (default: False)
            hide_stream_names: If True, omit stream label from stream metrics (default: False)
            hist_aggregation: Histogram aggregation mode (default: explicit_bucket_histogram)
            buckets_operation_duration: Explicit buckets (seconds) for db.client.operation.duration
            buckets_stream_processing_duration: Explicit buckets (seconds) for redis.client.stream.processing_duration
            buckets_connection_create_time: Buckets for db.client.connection.create_time
            buckets_connection_wait_time: Buckets for db.client.connection.wait_time
            buckets_connection_use_time: Buckets for db.client.connection.use_time
        """
        # Core enablement
        self.enabled = enabled
        self.enabled_metric_groups = set(enabled_metric_groups) if enabled_metric_groups else self.DEFAULT_METRIC_GROUPS

        # Command filtering
        self.include_commands = set(cmd.upper() for cmd in include_commands) if include_commands else None
        self.exclude_commands = set(cmd.upper() for cmd in exclude_commands) if exclude_commands else set()

        # Cardinality reduction
        self.hide_pubsub_channel_names = hide_pubsub_channel_names
        self.hide_stream_names = hide_stream_names

        # Histogram configuration
        self.hist_aggregation = hist_aggregation
        self.buckets_operation_duration = buckets_operation_duration or self.DEFAULT_BUCKETS_OPERATION_DURATION
        self.buckets_stream_processing_duration = buckets_stream_processing_duration or self.DEFAULT_BUCKETS_STREAM_PROCESSING_DURATION
        self.buckets_connection_create_time = buckets_connection_create_time or self.DEFAULT_BUCKETS_CONNECTION_CREATE_TIME
        self.buckets_connection_wait_time = buckets_connection_wait_time or self.DEFAULT_BUCKETS_CONNECTION_WAIT_TIME
        self.buckets_connection_use_time = buckets_connection_use_time or self.DEFAULT_BUCKETS_CONNECTION_USE_TIME

        # Validate configuration
        self._validate()

    def _validate(self) -> None:
        """Validate configuration settings."""
        # Validate metric groups
        valid_groups = {MetricGroup.COMMAND, MetricGroup.CONNECTION_BASIC, MetricGroup.RESILIENCY}
        for group in self.enabled_metric_groups:
            if group not in valid_groups:
                raise ValueError(f"Invalid metric group: {group}. Valid groups: {valid_groups}")

        # Validate histogram aggregation
        valid_aggs = {HistogramAggregation.EXPLICIT_BUCKET_HISTOGRAM, HistogramAggregation.BASE2_EXPONENTIAL_BUCKET_HISTOGRAM}
        if self.hist_aggregation not in valid_aggs:
            raise ValueError(f"Invalid histogram aggregation: {self.hist_aggregation}. Valid: {valid_aggs}")

        # Validate bucket boundaries (must be sorted and positive)
        if self.hist_aggregation == HistogramAggregation.EXPLICIT_BUCKET_HISTOGRAM:
            for name, buckets in [
                ("buckets_operation_duration", self.buckets_operation_duration),
                ("buckets_stream_processing_duration", self.buckets_stream_processing_duration),
                ("buckets_connection_create_time", self.buckets_connection_create_time),
                ("buckets_connection_wait_time", self.buckets_connection_wait_time),
                ("buckets_connection_use_time", self.buckets_connection_use_time),
            ]:
                if buckets:
                    if not all(b > 0 for b in buckets):
                        raise ValueError(f"{name} must contain only positive values")
                    if buckets != sorted(buckets):
                        raise ValueError(f"{name} must be sorted in ascending order")

    def is_metric_group_enabled(self, group: str) -> bool:
        """Check if a specific metric group is enabled."""
        return group in self.enabled_metric_groups

    def should_track_command(self, command_name: str) -> bool:
        """
        Determine if a command should be tracked based on include/exclude lists.

        Args:
            command_name: The Redis command name (e.g., 'GET', 'SET')

        Returns:
            True if the command should be tracked, False otherwise
        """
        command_upper = command_name.upper()

        # If include list is specified, only track commands in the list
        if self.include_commands is not None:
            return command_upper in self.include_commands

        # Otherwise, track all commands except those in exclude list
        return command_upper not in self.exclude_commands


class OTelConfig:
    """
    Configuration for OpenTelemetry observability in redis-py.

    This class manages all OTel-related settings including metrics, traces (future),
    and logs (future). Configuration is grouped by feature area.

    Args:
        metrics: MetricsConfig instance for metrics configuration (optional)

    Example:
        >>> from redis.observability import OTelConfig, MetricsConfig, MetricGroup
        >>>
        >>> # Simple usage - enable metrics with defaults
        >>> config = OTelConfig(metrics=MetricsConfig(enabled=True))
        >>>
        >>> # Advanced usage - customize metrics
        >>> config = OTelConfig(
        ...     metrics=MetricsConfig(
        ...         enabled=True,
        ...         enabled_metric_groups=[MetricGroup.COMMAND, MetricGroup.CONNECTION_BASIC],
        ...         include_commands=["GET", "SET"],
        ...         buckets_operation_duration=[0.001, 0.01, 0.1, 1.0],
        ...     )
        ... )
    """

    def __init__(
        self,
        metrics: Optional[MetricsConfig] = None,
    ):
        """
        Initialize OTel configuration.

        Args:
            metrics: Metrics configuration (default: disabled)
        """
        self.metrics = metrics if metrics is not None else MetricsConfig(enabled=False)

    def is_enabled(self) -> bool:
        """Check if any observability feature is enabled."""
        return self.metrics.enabled

    # Backward compatibility properties - delegate to metrics config
    @property
    def enable_metrics(self) -> bool:
        """Backward compatibility: access metrics.enable"""
        return self.metrics.enabled

    @property
    def enabled_metric_groups(self):
        """Backward compatibility: access metrics.enabled_metric_groups"""
        return self.metrics.enabled_metric_groups

    @property
    def include_commands(self):
        """Backward compatibility: access metrics.include_commands"""
        return self.metrics.include_commands

    @property
    def exclude_commands(self):
        """Backward compatibility: access metrics.exclude_commands"""
        return self.metrics.exclude_commands

    @property
    def hide_pubsub_channel_names(self) -> bool:
        """Backward compatibility: access metrics.hide_pubsub_channel_names"""
        return self.metrics.hide_pubsub_channel_names

    @property
    def hide_stream_names(self) -> bool:
        """Backward compatibility: access metrics.hide_stream_names"""
        return self.metrics.hide_stream_names

    @property
    def hist_aggregation(self):
        """Backward compatibility: access metrics.hist_aggregation"""
        return self.metrics.hist_aggregation

    @property
    def buckets_operation_duration(self):
        """Backward compatibility: access metrics.buckets_operation_duration"""
        return self.metrics.buckets_operation_duration

    @property
    def buckets_stream_processing_duration(self):
        """Backward compatibility: access metrics.buckets_stream_processing_duration"""
        return self.metrics.buckets_stream_processing_duration

    @property
    def buckets_connection_create_time(self):
        """Backward compatibility: access metrics.buckets_connection_create_time"""
        return self.metrics.buckets_connection_create_time

    @property
    def buckets_connection_wait_time(self):
        """Backward compatibility: access metrics.buckets_connection_wait_time"""
        return self.metrics.buckets_connection_wait_time

    @property
    def buckets_connection_use_time(self):
        """Backward compatibility: access metrics.buckets_connection_use_time"""
        return self.metrics.buckets_connection_use_time

    def is_metric_group_enabled(self, group: str) -> bool:
        """Check if a specific metric group is enabled."""
        return self.metrics.is_metric_group_enabled(group)

    def should_track_command(self, command_name: str) -> bool:
        """Determine if a command should be tracked based on include/exclude lists."""
        return self.metrics.should_track_command(command_name)

    def __repr__(self) -> str:
        return (
            f"OTelConfig(metrics.enable={self.metrics.enabled}, "
        )

