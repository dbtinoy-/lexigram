"""Subscription Manager for GraphQL subscriptions.

Manages active subscription streams per connection.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING, Any

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = get_logger(__name__)


class SubscriptionManager:
    """Manages active subscription streams per connection.

    Tracks subscriptions per connection and provides lifecycle management.
    Supports optional keepalive pings to prevent load-balancer idle timeouts
    on long-lived WebSocket connections.
    """

    def __init__(self, keepalive_interval: float = 25.0) -> None:
        # connection_id -> {subscription_id -> task}
        self._subscriptions: dict[str, dict[str, asyncio.Task]] = {}
        # connection_id -> {subscription_id -> AsyncIterator}
        self._streams: dict[str, dict[str, AsyncGenerator]] = {}
        # connection_id -> keepalive task
        self._keepalive_tasks: dict[str, asyncio.Task] = {}
        self._keepalive_interval = keepalive_interval

    async def subscribe(
        self,
        connection_id: str,
        subscription_id: str,
        stream: AsyncGenerator,
    ) -> None:
        """Register a new subscription.

        Args:
            connection_id: The WebSocket connection ID.
            subscription_id: The unique subscription ID.
            stream: The async generator yielding subscription results.
        """
        if connection_id not in self._subscriptions:
            self._subscriptions[connection_id] = {}
            self._streams[connection_id] = {}

        # Create task to run the stream
        async def run_stream() -> None:
            try:
                async for _ in stream:
                    pass  # Results are consumed; clients pull from _streams directly
            except asyncio.CancelledError:
                logger.debug("Subscription %s cancelled", subscription_id)
                raise
            except Exception as _sub_err:  # noqa: BLE001 — subscription stream workers must log any error before re-raising
                logger.exception("Error in subscription %s", subscription_id)
                raise

        task: asyncio.Task[None] = asyncio.create_task(run_stream())
        self._subscriptions[connection_id][subscription_id] = task
        self._streams[connection_id][subscription_id] = stream

        logger.debug(
            "Subscription %s started for connection %s", subscription_id, connection_id
        )

    async def unsubscribe(
        self,
        connection_id: str,
        subscription_id: str,
    ) -> None:
        """Unsubscribe from a specific subscription.

        Args:
            connection_id: The WebSocket connection ID.
            subscription_id: The subscription ID to cancel.
        """
        if connection_id not in self._subscriptions:
            return

        if subscription_id in self._subscriptions[connection_id]:
            task = self._subscriptions[connection_id][subscription_id]
            task.cancel()

            with contextlib.suppress(asyncio.CancelledError):
                await task

            del self._subscriptions[connection_id][subscription_id]

            if subscription_id in self._streams[connection_id]:
                del self._streams[connection_id][subscription_id]

            logger.debug(
                "Subscription %s stopped for connection %s",
                subscription_id,
                connection_id,
            )

        # Clean up empty connections
        if not self._subscriptions[connection_id]:
            del self._subscriptions[connection_id]
            if connection_id in self._streams:
                del self._streams[connection_id]

    async def disconnect(self, connection_id: str) -> None:
        """Clean up all subscriptions and keepalive for a connection.

        Args:
            connection_id: The WebSocket connection ID to disconnect.
        """
        await self.stop_keepalive(connection_id)

        if connection_id not in self._subscriptions:
            return

        # Cancel all subscriptions
        for subscription_id in list(self._subscriptions[connection_id].keys()):
            await self.unsubscribe(connection_id, subscription_id)

        logger.debug("All subscriptions cleaned up for connection %s", connection_id)

    async def start_keepalive(
        self,
        connection_id: str,
        send_ping: Any,
    ) -> None:
        """Start a keepalive loop for a WebSocket connection.

        Sends a ping every ``keepalive_interval`` seconds so load-balancer
        idle-connection timeouts do not silently drop long-lived subscriptions.

        Args:
            connection_id: The WebSocket connection ID.
            send_ping: Async callable that sends the keepalive message to the
                client (e.g., a WebSocket ``send_json`` partial).  It will be
                called with no arguments on each tick.
        """
        if connection_id in self._keepalive_tasks:
            return  # already running

        task: asyncio.Task[None] = asyncio.create_task(
            self._keepalive_loop(connection_id, send_ping),
            name=f"keepalive:{connection_id}",
        )
        self._keepalive_tasks[connection_id] = task
        task.add_done_callback(
            lambda _t: self._keepalive_tasks.pop(connection_id, None)
        )
        logger.debug("Keepalive started for connection %s", connection_id)

    async def stop_keepalive(self, connection_id: str) -> None:
        """Cancel the keepalive loop for a connection.

        Args:
            connection_id: The WebSocket connection ID.
        """
        task = self._keepalive_tasks.pop(connection_id, None)
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            logger.debug("Keepalive stopped for connection %s", connection_id)

    async def _keepalive_loop(self, connection_id: str, send_ping: Any) -> None:
        """Send periodic pings until cancelled.

        Args:
            connection_id: Used only for log messages.
            send_ping: Async callable invoked on each keepalive tick.
        """
        while True:
            await asyncio.sleep(self._keepalive_interval)
            try:
                await send_ping()
                logger.debug("Keepalive ping sent for connection %s", connection_id)
            except asyncio.CancelledError:
                raise
            except (OSError, RuntimeError) as e:
                logger.warning(
                    "Keepalive ping failed for connection %s; stopping loop: %s",
                    connection_id,
                    e,
                )
                break

    def get_active_subscriptions(self, connection_id: str) -> list[str]:
        """Get list of active subscription IDs for a connection.

        Args:
            connection_id: The WebSocket connection ID.

        Returns:
            List of active subscription IDs.
        """
        if connection_id not in self._subscriptions:
            return []
        return list(self._subscriptions[connection_id].keys())

    @property
    def active_count(self) -> int:
        """Get total number of active subscriptions across all connections."""
        return sum(len(subs) for subs in self._subscriptions.values())

    @property
    def connection_count(self) -> int:
        """Get number of active connections."""
        return len(self._subscriptions)


__all__ = ["SubscriptionManager"]
