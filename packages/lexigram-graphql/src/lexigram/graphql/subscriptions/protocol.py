"""GraphQL subscription protocol definitions.

Defines message types and constants for the graphql-transport-ws protocol.
"""

from __future__ import annotations

from enum import StrEnum


class GQLWSMessageType(StrEnum):
    """GraphQL-WS message types (graphql-transport-ws protocol)."""

    # Connection
    CONNECTION_INIT = "connection_init"
    CONNECTION_ACK = "connection_ack"
    CONNECTION_ERROR = "connection_error"
    CONNECTION_KEEP_ALIVE = "ka"

    # Subscription
    SUBSCRIBE = "subscribe"
    NEXT = "next"
    ERROR = "error"
    COMPLETE = "complete"

    # Ping/Pong
    PING = "ping"
    PONG = "pong"


# Protocol constants
PROTOCOL_NAME_LEGACY = "graphql-ws"
PROTOCOL_NAME_TRANSPORT_WS = "graphql-transport-ws"

DEFAULT_KEEPALIVE_INTERVAL = 30.0  # seconds
DEFAULT_CONNECTION_TIMEOUT = 10.0  # seconds

# Error codes
ERROR_CODE_INTERNAL = "INTERNAL_ERROR"
ERROR_CODE_AUTH_NOT_SUPPORTED = "AUTH_NOT_SUPPORTED"
ERROR_CODE_AUTH_INVALID = "AUTH_INVALID"
ERROR_CODE_BAD_REQUEST = "BAD_REQUEST"
ERROR_CODE_OPERATION_RESULT = "OPERATION_RESULT_ERROR"


__all__ = [
    "DEFAULT_CONNECTION_TIMEOUT",
    "DEFAULT_KEEPALIVE_INTERVAL",
    "ERROR_CODE_AUTH_INVALID",
    "ERROR_CODE_AUTH_NOT_SUPPORTED",
    "ERROR_CODE_BAD_REQUEST",
    "ERROR_CODE_INTERNAL",
    "ERROR_CODE_OPERATION_RESULT",
    "PROTOCOL_NAME_LEGACY",
    "PROTOCOL_NAME_TRANSPORT_WS",
    "GQLWSMessageType",
]
