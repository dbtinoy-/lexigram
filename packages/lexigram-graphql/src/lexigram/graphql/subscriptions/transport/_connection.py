"""GraphQL WebSocket Transport for subscriptions.

Provides WebSocket transport implementation using graphql-transport-ws protocol.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

from lexigram import serialization as json
from lexigram.graphql.subscriptions.protocol import GQLWSMessageType
from lexigram.graphql.types import SubscriptionInfo
from lexigram.logging import get_logger



logger = get_logger(__name__)


@dataclass
class SubscriptionConnection:
    """Manages active subscriptions for a WebSocket connection."""

    subscriptions: dict[str, SubscriptionInfo] = field(default_factory=dict)

    def add(self, subscription_id: str, info: SubscriptionInfo) -> None:
        """Add a subscription."""
        self.subscriptions[subscription_id] = info

    def remove(self, subscription_id: str) -> None:
        """Remove a subscription."""
        self.subscriptions.pop(subscription_id, None)

    def get(self, subscription_id: str) -> SubscriptionInfo | None:
        """Get a subscription by ID."""
        return self.subscriptions.get(subscription_id)
