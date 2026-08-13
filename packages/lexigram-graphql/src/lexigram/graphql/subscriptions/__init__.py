"""GraphQL Subscription WebSocket Transport.

This module provides WebSocket transport for GraphQL subscriptions
using the graphql-transport-ws protocol.
"""

from __future__ import annotations

from lexigram.graphql.subscriptions.auth import (
    SubscriptionAuth,
    default_auth,
)
from lexigram.graphql.subscriptions.manager import SubscriptionManager
from lexigram.graphql.subscriptions.protocol import (
    PROTOCOL_NAME_LEGACY,
    PROTOCOL_NAME_TRANSPORT_WS,
    GQLWSMessageType,
)
from lexigram.graphql.subscriptions.transport import (
    GraphQLWSHandler,
    GraphQLWSTransport,
    SubscriptionConnection,
    SubscriptionInfo,
)

__all__ = [
    "PROTOCOL_NAME_LEGACY",
    "PROTOCOL_NAME_TRANSPORT_WS",
    # Protocol
    "GQLWSMessageType",
    # Transport
    "GraphQLWSHandler",
    "GraphQLWSTransport",
    # Auth
    "SubscriptionAuth",
    "SubscriptionConnection",
    "SubscriptionInfo",
    # Manager
    "SubscriptionManager",
    "default_auth",
]
