"""
OpenTelemetry semantic convention attributes for Redis.

This module provides constants and helper functions for building OTel attributes
according to the semantic conventions for database clients.

Reference: https://opentelemetry.io/docs/specs/semconv/database/redis/
"""

from typing import Any, Dict, Optional


# Database semantic convention attributes
DB_SYSTEM = "db.system"
DB_NAMESPACE = "db.namespace"
DB_OPERATION_NAME = "db.operation.name"
DB_OPERATION_BATCH_SIZE = "db.operation.batch.size"
DB_RESPONSE_STATUS_CODE = "db.response.status_code"
DB_STORED_PROCEDURE_NAME = "db.stored_procedure.name"

# Error attributes
ERROR_TYPE = "error.type"

# Network attributes
NETWORK_PEER_ADDRESS = "network.peer.address"
NETWORK_PEER_PORT = "network.peer.port"

# Server attributes
SERVER_ADDRESS = "server.address"
SERVER_PORT = "server.port"

# Connection pool attributes
DB_CLIENT_CONNECTION_POOL_NAME = "db.client.connection.pool.name"
DB_CLIENT_CONNECTION_STATE = "db.client.connection.state"

# Redis-specific attributes
REDIS_CLIENT_LIBRARY = "redis.client.library"
REDIS_CLIENT_CONNECTION_PUBSUB = "redis.client.connection.pubsub"
REDIS_CLIENT_CONNECTION_CLOSE_REASON = "redis.client.connection.close.reason"
REDIS_CLIENT_OPERATION_RETRY_ATTEMPTS = "redis.client.operation.retry_attempts"
REDIS_CLIENT_OPERATION_BLOCKING = "redis.client.operation.blocking"
REDIS_CLIENT_PUBSUB_MESSAGE_DIRECTION = "redis.client.pubsub.message.direction"

# Connection states
CONNECTION_STATE_IDLE = "idle"
CONNECTION_STATE_USED = "used"

# PubSub message directions
PUBSUB_DIRECTION_PUBLISH = "publish"
PUBSUB_DIRECTION_RECEIVE = "receive"


class AttributeBuilder:
    """
    Helper class to build OTel semantic convention attributes for Redis operations.
    """
    
    @staticmethod
    def build_base_attributes(
        server_address: Optional[str] = None,
        server_port: Optional[int] = None,
        db_namespace: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Build base attributes common to all Redis operations.
        
        Args:
            server_address: Redis server address (FQDN or IP)
            server_port: Redis server port
            db_namespace: Redis database index
        
        Returns:
            Dictionary of base attributes
        """
        attrs = {
            DB_SYSTEM: "redis",
        }
        
        if server_address is not None:
            attrs[SERVER_ADDRESS] = server_address
        
        if server_port is not None:
            attrs[SERVER_PORT] = server_port
        
        if db_namespace is not None:
            attrs[DB_NAMESPACE] = str(db_namespace)
        
        return attrs
    
    @staticmethod
    def build_operation_attributes(
        command_name: str,
        batch_size: Optional[int] = None,
        response_status_code: Optional[str] = None,
        error_type: Optional[str] = None,
        network_peer_address: Optional[str] = None,
        network_peer_port: Optional[int] = None,
        stored_procedure_name: Optional[str] = None,
        retry_attempts: Optional[int] = None,
        is_blocking: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Build attributes for a Redis operation (command execution).

        Args:
            command_name: Redis command name (e.g., 'GET', 'SET', 'MULTI')
            batch_size: Number of commands in batch (for pipelines/transactions)
            response_status_code: Redis error prefix (e.g., 'ERR', 'WRONGTYPE')
            error_type: Error type if operation failed
            network_peer_address: Resolved peer address
            network_peer_port: Peer port number
            stored_procedure_name: Lua script name or SHA1 digest
            retry_attempts: Number of retry attempts made
            is_blocking: Whether the operation is a blocking command

        Returns:
            Dictionary of operation attributes
        """
        attrs = {
            DB_OPERATION_NAME: command_name.upper(),
        }

        if batch_size is not None and batch_size >= 2:
            attrs[DB_OPERATION_BATCH_SIZE] = batch_size

        if response_status_code is not None:
            attrs[DB_RESPONSE_STATUS_CODE] = response_status_code

        if error_type is not None:
            attrs[ERROR_TYPE] = error_type

        if network_peer_address is not None:
            attrs[NETWORK_PEER_ADDRESS] = network_peer_address

        if network_peer_port is not None:
            attrs[NETWORK_PEER_PORT] = network_peer_port

        if stored_procedure_name is not None:
            attrs[DB_STORED_PROCEDURE_NAME] = stored_procedure_name

        if retry_attempts is not None and retry_attempts > 0:
            attrs[REDIS_CLIENT_OPERATION_RETRY_ATTEMPTS] = retry_attempts

        if is_blocking is not None:
            attrs[REDIS_CLIENT_OPERATION_BLOCKING] = is_blocking

        return attrs
    
    @staticmethod
    def build_connection_pool_attributes(
        pool_name: str,
        connection_state: Optional[str] = None,
        is_pubsub: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Build attributes for connection pool metrics.

        Args:
            pool_name: Unique connection pool name
            connection_state: Connection state ('idle' or 'used')
            is_pubsub: Whether this is a PubSub connection

        Returns:
            Dictionary of connection pool attributes
        """
        attrs = {
            DB_SYSTEM: "redis",
            DB_CLIENT_CONNECTION_POOL_NAME: pool_name,
        }

        if connection_state is not None:
            attrs[DB_CLIENT_CONNECTION_STATE] = connection_state

        if is_pubsub is not None:
            attrs[REDIS_CLIENT_CONNECTION_PUBSUB] = is_pubsub

        return attrs
    
    @staticmethod
    def build_cluster_redirection_attributes(
        redirection_kind: str,
    ) -> Dict[str, Any]:
        """
        Build attributes for cluster redirection metrics.
        
        Args:
            redirection_kind: Type of redirection ('MOVED' or 'ASK')
        
        Returns:
            Dictionary of redirection attributes
        """
        return {
            REDIS_CLIENT_REDIRECTION_KIND: redirection_kind,
        }
    
    @staticmethod
    def extract_error_type(exception: Exception) -> str:
        """
        Extract error type from an exception.
        
        Args:
            exception: The exception that occurred
        
        Returns:
            Error type string (exception class name)
        """
        return type(exception).__name__
    
    @staticmethod
    def extract_response_status_code(exception: Exception) -> Optional[str]:
        """
        Extract Redis error prefix from a ResponseError.
        
        Args:
            exception: The exception that occurred
        
        Returns:
            Redis error prefix (e.g., 'ERR', 'WRONGTYPE') or None
        """
        # Import here to avoid circular dependency
        from redis.exceptions import ResponseError
        
        if isinstance(exception, ResponseError):
            error_msg = str(exception)
            # Redis error format: "ERR message" or "WRONGTYPE message"
            if " " in error_msg:
                prefix = error_msg.split(" ", 1)[0]
                # Common Redis error prefixes
                if prefix in [
                    "ERR", "WRONGTYPE", "CLUSTERDOWN", "MOVED", "ASK",
                    "TRYAGAIN", "CROSSSLOT", "READONLY", "NOAUTH", "NOPERM"
                ]:
                    return prefix
        
        return None
    
    @staticmethod
    def build_pool_name(
        server_address: str,
        server_port: int,
        db_namespace: int = 0,
    ) -> str:
        """
        Build a unique connection pool name.
        
        Args:
            server_address: Redis server address
            server_port: Redis server port
            db_namespace: Redis database index
        
        Returns:
            Unique pool name in format "address:port/db"
        """
        return f"{server_address}:{server_port}/{db_namespace}"

