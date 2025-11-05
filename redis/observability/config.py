"""
OpenTelemetry configuration for redis-py.

This module handles configuration for OTel observability features,
including parsing environment variables and validating settings.
"""

import os
from typing import Dict, List, Optional, Union


class OTelConfig:
    """
    Configuration for OpenTelemetry observability in redis-py.
    
    This class manages all OTel-related settings including metrics, traces (future),
    and logs (future). Configuration can be provided via constructor parameters or
    environment variables (OTEL_* spec).
    
    Constructor parameters take precedence over environment variables.
    
    Args:
        enable_metrics: Enable/disable metrics emission (default: False)
        enable_traces: Enable/disable tracing (default: False) - Phase 2
        enable_logs: Enable/disable log export (default: False) - Phase 3
        metrics_sample_percentage: Percentage of commands to sample (default: 100.0, range: 0.0-100.0)
        include_commands: Explicit allowlist of commands to track
        exclude_commands: Blocklist of commands to track

    Note:
        Redis-py uses the global MeterProvider set by your application.
        Set it up before initializing observability:

            from opentelemetry import metrics
            from opentelemetry.sdk.metrics import MeterProvider
            from opentelemetry.sdk.metrics._internal.view import View
            from opentelemetry.sdk.metrics._internal.aggregation import ExplicitBucketHistogramAggregation

            # Configure histogram bucket boundaries via Views
            views = [
                View(
                    instrument_name="db.client.operation.duration",
                    aggregation=ExplicitBucketHistogramAggregation(
                        boundaries=[0.0001, 0.00025, 0.0005, 0.001, 0.0025, 0.005,
                                    0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5]
                    ),
                ),
                # Add more views for other histograms...
            ]

            provider = MeterProvider(views=views, metric_readers=[reader])
            metrics.set_meter_provider(provider)

            # Then initialize redis-py observability
            from redis.observability import get_observability_instance, OTelConfig
            otel = get_observability_instance()
            otel.init(OTelConfig(enable_metrics=True))
    """
    

    def __init__(
        self,
        # Core enablement
        enable_metrics: bool = False,
        enable_traces: bool = False,
        enable_logs: bool = False,
        # Metrics-specific
        metrics_sample_percentage: float = 100.0,
        # Redis-specific telemetry controls
        include_commands: Optional[List[str]] = None,
        exclude_commands: Optional[List[str]] = None,
    ):
        # Core enablement
        self.enable_metrics = enable_metrics
        self.enable_traces = enable_traces
        self.enable_logs = enable_logs

        # Metrics configuration
        if not 0.0 <= metrics_sample_percentage <= 100.0:
            raise ValueError(
                f"metrics_sample_percentage must be between 0.0 and 100.0, "
                f"got {metrics_sample_percentage}"
            )
        self.metrics_sample_percentage = metrics_sample_percentage

        # Redis-specific controls
        self.include_commands = set(include_commands) if include_commands else None
        self.exclude_commands = set(exclude_commands) if exclude_commands else set()

        # Validate configuration
        self._validate()
    
    def _validate(self) -> None:
        """Validate configuration settings."""
        # No validation needed - we use global MeterProvider set by the application
        pass
    
    def is_enabled(self) -> bool:
        """Check if any observability feature is enabled."""
        return self.enable_metrics or self.enable_traces or self.enable_logs
    
    def set_sample_percentage(self, percentage: float) -> None:
        """
        Set the metrics sample percentage at runtime.

        This allows dynamic adjustment of sampling rate for high-throughput deployments.

        Args:
            percentage: Percentage of commands to sample (0.0-100.0)

        Raises:
            ValueError: If percentage is not in valid range

        Example:
            >>> config.set_sample_percentage(10.0)  # Sample 10% of commands
        """
        if not 0.0 <= percentage <= 100.0:
            raise ValueError(
                f"metrics_sample_percentage must be between 0.0 and 100.0, "
                f"got {percentage}"
            )
        self.metrics_sample_percentage = percentage

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
    
    def get_endpoint_with_default_port(self) -> Optional[str]:
        """
        Get the collector endpoint with default port inferred if needed.
        
        Returns:
            Endpoint with port, or None if no endpoint configured
        """
        if not self.collector_endpoint:
            return None
        
        endpoint = self.collector_endpoint
        
        # If endpoint doesn't have a port, infer default based on protocol
        if "://" in endpoint:
            scheme, rest = endpoint.split("://", 1)
            if ":" not in rest.split("/")[0]:  # No port specified
                if self.protocol == "grpc":
                    endpoint = f"{scheme}://{rest.split('/')[0]}:4317"
                else:  # http/protobuf
                    endpoint = f"{scheme}://{rest.split('/')[0]}:4318"
                # Preserve path if any
                if "/" in rest:
                    endpoint += "/" + "/".join(rest.split("/")[1:])
        
        return endpoint
    
    def __repr__(self) -> str:
        return (
            f"OTelConfig(enable_metrics={self.enable_metrics}, "
            f"collector_endpoint={self.collector_endpoint}, "
            f"protocol={self.protocol})"
        )

