"""GraphQL WebSocket Transport for subscriptions.

Provides WebSocket transport implementation using graphql-transport-ws protocol.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

from lexigram import serialization as json
from lexigram.graphql.subscriptions.protocol import GQLWSMessageType
from lexigram.graphql.subscriptions.transport._connection import SubscriptionConnection
from lexigram.graphql.types import SubscriptionInfo
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

    from lexigram.contracts.graphql.protocols import SubscriptionAuthHandlerProtocol
    from lexigram.contracts.web import WebSocketProtocol

logger = get_logger(__name__)

@dataclass

class _WSMessagingMixin:
    """Send/error/complete framing plus keepalive and cleanup."""
    _websocket: WebSocketProtocol | None
    _connection: SubscriptionConnection | None
    _connection_ack_sent: bool
    keepalive_interval: float
    async def _send_message(self, message: dict[str, Any]) -> None:
        """Send a message to the client.

        Args:
            message: The message to send.
        """
        if not self._websocket:
            return
        try:
            await self._websocket.send_json(message)
        except Exception as e:
            if type(e).__name__ == "WebSocketDisconnect":
                logger.debug("WebSocket disconnected while sending: %s", e)
            else:
                raise

    async def _send_next(self, subscription_id: str, data: Any) -> None:
        """Send next message (subscription data).

        Args:
            subscription_id: The subscription ID.
            data: The data to send.
        """
        # Convert ExecutionResult to dict if needed
        payload_data = None
        if data is not None:
            if hasattr(data, "data"):
                payload_data = data.data
            elif hasattr(data, "__dict__"):
                payload_data = data.__dict__
            else:
                payload_data = data

        await self._send_message(
            {
                "id": subscription_id,
                "type": GQLWSMessageType.NEXT,
                "payload": {"data": payload_data} if payload_data else {},
            }
        )

    async def _send_error(self, subscription_id: str | None, error: str) -> None:
        """Send error message.

        Args:
            subscription_id: The subscription ID (may be None for connection errors).
            error: The error message.
        """
        await self._send_message(
            {
                "id": subscription_id,
                "type": GQLWSMessageType.ERROR,
                "payload": {"message": error},
            }
        )

    async def _send_complete(self, subscription_id: str) -> None:
        """Send complete message.

        Args:
            subscription_id: The subscription ID.
        """
        await self._send_message(
            {
                "id": subscription_id,
                "type": GQLWSMessageType.COMPLETE,
            }
        )

    async def _keepalive(self) -> None:
        """Send keep-alive ping messages (graphql-transport-ws protocol)."""
        try:
            while True:
                await asyncio.sleep(self.keepalive_interval)
                if self._websocket and self._connection_ack_sent:
                    await self._send_message({"type": GQLWSMessageType.PING})
        except asyncio.CancelledError:
            pass

    async def _cleanup(self) -> None:
        """Clean up resources on disconnect."""
        if self._connection:
            # Cancel all active subscriptions
            for sub_id in list(self._connection.subscriptions.keys()):
                self._connection.remove(sub_id)
        self._connection = None
        self._websocket = None

    # ------------------------------------------------------------------
    # SubscriptionHandler protocol implementation
    # ------------------------------------------------------------------

