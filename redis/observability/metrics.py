"""
OpenTelemetry metrics collector for redis-py.

This module defines and manages all metric instruments according to
OTel semantic conventions for database clients.
"""

import logging
import time
from typing import Any, Dict, Optional

from redis.observability.attributes import AttributeBuilder
from redis.observability.config import OTelConfig

logger = logging.getLogger(__name__)

# Optional imports - OTel SDK may not be installed
try:
    from opentelemetry.metrics import Counter, Histogram, Meter, UpDownCounter
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    Counter = None
    Histogram = None
    Meter = None
    UpDownCounter = None


class RedisMetricsCollector:
    """
    Collects and records OpenTelemetry metrics for Redis operations.
    
    This class manages all metric instruments and provides methods to record
    various Redis operations including connection pool events, command execution,
    and cluster-specific operations.
    
    Args:
        meter: OpenTelemetry Meter instance
        config: OTel configuration object
    """
    
    METER_NAME = "redis-py"
    METER_VERSION = "1.0.0"
    
    def __init__(self, meter: "Meter", config: OTelConfig):
        if not OTEL_AVAILABLE:
            raise ImportError(
                "OpenTelemetry API is not installed. "
                "Install it with: pip install opentelemetry-api"
            )
        
        self.meter = meter
        self.config = config
        self.attr_builder = AttributeBuilder()
        
        # Initialize all metric instruments
        self._init_connection_metrics()
        self._init_command_metrics()
        self._init_cluster_metrics()
        self._init_pubsub_metrics()

        logger.info("RedisMetricsCollector initialized")
    
    def _init_connection_metrics(self) -> None:
        """Initialize connection pool metric instruments."""
        # Connection count by state (idle/used)
        self.connection_count = self.meter.create_up_down_counter(
            name="db.client.connection.count",
            unit="{connection}",
            description="Current connections by state (idle/used)",
        )
        
        # Connection pool limits
        self.connection_idle_max = self.meter.create_up_down_counter(
            name="db.client.connection.idle.max",
            unit="{connection}",
            description="Maximum number of idle open connections allowed",
        )
        
        self.connection_idle_min = self.meter.create_up_down_counter(
            name="db.client.connection.idle.min",
            unit="{connection}",
            description="Minimum number of idle open connections allowed",
        )
        
        self.connection_max = self.meter.create_up_down_counter(
            name="db.client.connection.max",
            unit="{connection}",
            description="Maximum number of open connections allowed",
        )
        
        # Pending requests
        self.connection_pending_requests = self.meter.create_up_down_counter(
            name="db.client.connection.pending_requests",
            unit="{request}",
            description="Number of pending requests for an open connection",
        )
        
        # Connection timeouts
        self.connection_timeouts = self.meter.create_counter(
            name="db.client.connection.timeouts",
            unit="{timeout}",
            description="Number of connection timeouts",
        )
        
        # Connection timing histograms
        self.connection_create_time = self.meter.create_histogram(
            name="db.client.connection.create_time",
            unit="s",
            description="Time to create a new connection",
        )
        
        self.connection_wait_time = self.meter.create_histogram(
            name="db.client.connection.wait_time",
            unit="s",
            description="Time to obtain an open connection from the pool",
        )
        
        self.connection_use_time = self.meter.create_histogram(
            name="db.client.connection.use_time",
            unit="s",
            description="Time between borrowing and returning a connection",
        )

        # Connection closed counter
        self.connection_closed = self.meter.create_counter(
            name="redis.client.connection.closed",
            unit="{connection}",
            description="Total number of closed connections",
        )

        # Relaxed timeout counter
        self.connection_relaxed_timeout = self.meter.create_up_down_counter(
            name="redis.client.connection.relaxed_timeout",
            unit="{relaxation}",
            description="Counts up for relaxed timeout, counts down for unrelaxed timeout",
        )

        # Connection handoff counter
        self.connection_handoff = self.meter.create_counter(
            name="redis.client.connection.handoff",
            unit="{handoff}",
            description="Connections that have been handed off (e.g., after a MOVING notification)",
        )

    def _init_command_metrics(self) -> None:
        """Initialize command execution metric instruments."""
        self.operation_duration = self.meter.create_histogram(
            name="db.client.operation.duration",
            unit="s",
            description="Command execution duration",
        )
    
    def _init_cluster_metrics(self) -> None:
        """Initialize cluster-specific and resiliency metric instruments."""
        # Errors handled internally (not surfaced to user)
        self.errors_handled = self.meter.create_counter(
            name="redis.client.errors.handled",
            unit="{error}",
            description="Errors handled internally in the client library and not surfaced to the user",
        )

    def _init_pubsub_metrics(self) -> None:
        """Initialize PubSub metric instruments."""
        self.pubsub_messages = self.meter.create_counter(
            name="redis.client.pubsub.messages",
            unit="{message}",
            description="Tracks published and received messages",
        )
    
    # Connection pool metric recording methods
    
    def record_connection_count(
        self,
        pool_name: str,
        state: str,
        count: int,
    ) -> None:
        """
        Record current connection count by state.
        
        Args:
            pool_name: Connection pool name
            state: Connection state ('idle' or 'used')
            count: Number of connections
        """
        attrs = self.attr_builder.build_connection_pool_attributes(
            pool_name=pool_name,
            connection_state=state,
        )
        self.connection_count.add(count, attributes=attrs)
    
    def record_connection_limits(
        self,
        pool_name: str,
        max_connections: Optional[int] = None,
        min_idle: Optional[int] = None,
        max_idle: Optional[int] = None,
    ) -> None:
        """
        Record connection pool limit configuration.
        
        Args:
            pool_name: Connection pool name
            max_connections: Maximum total connections
            min_idle: Minimum idle connections
            max_idle: Maximum idle connections
        """
        base_attrs = self.attr_builder.build_connection_pool_attributes(pool_name=pool_name)
        
        if max_connections is not None:
            self.connection_max.add(max_connections, attributes=base_attrs)
        
        if min_idle is not None:
            self.connection_idle_min.add(min_idle, attributes=base_attrs)
        
        if max_idle is not None:
            self.connection_idle_max.add(max_idle, attributes=base_attrs)
    
    def record_connection_timeout(self, pool_name: str) -> None:
        """
        Record a connection timeout event.
        
        Args:
            pool_name: Connection pool name
        """
        attrs = self.attr_builder.build_connection_pool_attributes(pool_name=pool_name)
        self.connection_timeouts.add(1, attributes=attrs)
    
    def record_connection_create_time(
        self,
        pool_name: str,
        duration_seconds: float,
    ) -> None:
        """
        Record time taken to create a new connection.
        
        Args:
            pool_name: Connection pool name
            duration_seconds: Creation time in seconds
        """
        attrs = self.attr_builder.build_connection_pool_attributes(pool_name=pool_name)
        self.connection_create_time.record(duration_seconds, attributes=attrs)
    
    def record_connection_wait_time(
        self,
        pool_name: str,
        duration_seconds: float,
    ) -> None:
        """
        Record time taken to obtain a connection from the pool.
        
        Args:
            pool_name: Connection pool name
            duration_seconds: Wait time in seconds
        """
        attrs = self.attr_builder.build_connection_pool_attributes(pool_name=pool_name)
        self.connection_wait_time.record(duration_seconds, attributes=attrs)
    
    def record_connection_use_time(
        self,
        pool_name: str,
        duration_seconds: float,
    ) -> None:
        """
        Record time a connection was in use (borrowed from pool).

        Args:
            pool_name: Connection pool name
            duration_seconds: Use time in seconds
        """
        attrs = self.attr_builder.build_connection_pool_attributes(pool_name=pool_name)
        self.connection_use_time.record(duration_seconds, attributes=attrs)

    # Command execution metric recording methods

    def record_operation_duration(
        self,
        command_name: str,
        duration_seconds: float,
        server_address: Optional[str] = None,
        server_port: Optional[int] = None,
        db_namespace: Optional[int] = None,
        batch_size: Optional[int] = None,
        response_status_code: Optional[str] = None,
        error_type: Optional[str] = None,
        network_peer_address: Optional[str] = None,
        network_peer_port: Optional[int] = None,
    ) -> None:

        """
        Record command execution duration.

        Args:
            command_name: Redis command name (e.g., 'GET', 'SET', 'MULTI')
            duration_seconds: Execution time in seconds
            server_address: Redis server address
            server_port: Redis server port
            db_namespace: Redis database index
            batch_size: Number of commands in batch (for pipelines/transactions)
            response_status_code: Redis error prefix if operation failed
            error_type: Error type if operation failed
            network_peer_address: Resolved peer address
            network_peer_port: Peer port number
        """

        # Check if this command should be tracked
        if not self.config.should_track_command(command_name):
            return

        # Build attributes
        attrs = self.attr_builder.build_base_attributes(
            server_address=server_address,
            server_port=server_port,
            db_namespace=db_namespace,
        )

        attrs.update(
            self.attr_builder.build_operation_attributes(
                command_name=command_name,
                batch_size=batch_size,
                response_status_code=response_status_code,
                error_type=error_type,
                network_peer_address=network_peer_address,
                network_peer_port=network_peer_port,
            )
        )

        self.operation_duration.record(duration_seconds, attributes=attrs)

    def record_connection_closed(
        self,
        pool_name: str,
        close_reason: Optional[str] = None,
        error_type: Optional[str] = None,
    ) -> None:
        """
        Record a connection closed event.

        Args:
            pool_name: Connection pool name
            close_reason: Reason for closing (e.g., 'idle_timeout', 'error', 'shutdown')
            error_type: Error type if closed due to error
        """
        attrs = self.attr_builder.build_connection_pool_attributes(pool_name=pool_name)
        if close_reason:
            attrs["redis.client.connection.close.reason"] = close_reason
        if error_type:
            attrs["error.type"] = error_type
        self.connection_closed.add(1, attributes=attrs)

    def record_connection_relaxed_timeout(
        self,
        pool_name: str,
        relaxed: bool,
    ) -> None:
        """
        Record a connection timeout relaxation event.

        Args:
            pool_name: Connection pool name
            relaxed: True to count up (relaxed), False to count down (unrelaxed)
        """
        attrs = self.attr_builder.build_connection_pool_attributes(pool_name=pool_name)
        self.connection_relaxed_timeout.add(1 if relaxed else -1, attributes=attrs)

    def record_connection_handoff(
        self,
        pool_name: str,
    ) -> None:
        """
        Record a connection handoff event (e.g., after MOVING notification).

        Args:
            pool_name: Connection pool name
        """
        attrs = self.attr_builder.build_connection_pool_attributes(pool_name=pool_name)
        self.connection_handoff.add(1, attributes=attrs)

    # Resiliency metric recording methods

    def record_error_handled(
        self,
        server_address: Optional[str] = None,
        server_port: Optional[int] = None,
        network_peer_address: Optional[str] = None,
        network_peer_port: Optional[int] = None,
        error_type: Optional[str] = None,
        response_status_code: Optional[str] = None,
    ) -> None:
        """
        Record an error that was handled internally and not surfaced to the user.

        This includes errors like MOVED, ASK, and other retryable errors.

        Args:
            server_address: Redis server address
            server_port: Redis server port
            network_peer_address: Resolved peer address
            network_peer_port: Peer port number
            error_type: Error type
            response_status_code: Redis error prefix
        """
        attrs = self.attr_builder.build_base_attributes(
            server_address=server_address,
            server_port=server_port,
        )
        if network_peer_address:
            attrs["network.peer.address"] = network_peer_address
        if network_peer_port:
            attrs["network.peer.port"] = network_peer_port
        if error_type:
            attrs["error.type"] = error_type
        if response_status_code:
            attrs["db.response.status_code"] = response_status_code

        self.errors_handled.add(1, attributes=attrs)

    # PubSub metric recording methods

    def record_pubsub_message(
        self,
        direction: str,
    ) -> None:
        """
        Record a PubSub message (published or received).

        Args:
            direction: Message direction ('publish' or 'receive')
        """
        attrs = self.attr_builder.build_base_attributes()
        attrs["redis.client.pubsub.message.direction"] = direction
        self.pubsub_messages.add(1, attributes=attrs)

    # Utility methods

    @staticmethod
    def monotonic_time() -> float:
        """
        Get monotonic time for duration measurements.

        Returns:
            Current monotonic time in seconds
        """
        return time.monotonic()

    def __repr__(self) -> str:
        return f"RedisMetricsCollector(meter={self.meter}, config={self.config})"

