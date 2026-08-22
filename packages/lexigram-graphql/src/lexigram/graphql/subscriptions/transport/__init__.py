"""Subscription transport package."""

from __future__ import annotations

from lexigram.graphql.subscriptions.transport._connection import SubscriptionConnection
from lexigram.graphql.subscriptions.transport._transport import (  # noqa: F401
    GraphQLWSTransport,
    SubscriptionInfo,  # re-exported for backward compatibility
    logger,
)
from lexigram.graphql.subscriptions.transport.handler import (
    GraphQLWSHandler,
    create_ws_route,
    graphql_ws_endpoint,
)

__all__ = [
    "GraphQLWSHandler",
    "SubscriptionInfo",
    "GraphQLWSTransport",
    "SubscriptionConnection",
    "create_ws_route",
    "graphql_ws_endpoint",
    "logger",
]
