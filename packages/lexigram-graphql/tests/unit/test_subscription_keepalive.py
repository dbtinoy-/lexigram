"""Tests for SubscriptionManager keepalive functionality."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from lexigram.graphql.subscriptions.manager import SubscriptionManager


class TestSubscriptionManagerKeepaliveStart:
    @pytest.mark.asyncio
    async def test_start_keepalive_creates_task(self) -> None:
        manager = SubscriptionManager(keepalive_interval=60.0)
        send_ping = AsyncMock()

        await manager.start_keepalive("conn-1", send_ping)

        assert "conn-1" in manager._keepalive_tasks
        manager._keepalive_tasks["conn-1"].cancel()

    @pytest.mark.asyncio
    async def test_start_keepalive_is_idempotent(self) -> None:
        """Calling start_keepalive twice does not create a second task."""
        manager = SubscriptionManager(keepalive_interval=60.0)
        send_ping = AsyncMock()

        await manager.start_keepalive("conn-1", send_ping)
        first_task = manager._keepalive_tasks["conn-1"]

        await manager.start_keepalive("conn-1", send_ping)
        second_task = manager._keepalive_tasks["conn-1"]

        assert first_task is second_task
        first_task.cancel()


class TestSubscriptionManagerKeepaliveStop:
    @pytest.mark.asyncio
    async def test_stop_keepalive_cancels_task(self) -> None:
        manager = SubscriptionManager(keepalive_interval=60.0)
        send_ping = AsyncMock()

        await manager.start_keepalive("conn-1", send_ping)
        task = manager._keepalive_tasks["conn-1"]

        await manager.stop_keepalive("conn-1")

        assert "conn-1" not in manager._keepalive_tasks
        assert task.cancelled()

    @pytest.mark.asyncio
    async def test_stop_keepalive_is_safe_when_not_started(self) -> None:
        manager = SubscriptionManager()
        # Should not raise
        await manager.stop_keepalive("nonexistent-conn")


class TestSubscriptionManagerKeepalivePings:
    @pytest.mark.asyncio
    async def test_keepalive_sends_periodic_pings(self) -> None:
        manager = SubscriptionManager(keepalive_interval=0.01)
        send_ping = AsyncMock()

        await manager.start_keepalive("conn-1", send_ping)

        # Allow at least one keepalive tick to fire
        await asyncio.sleep(0.05)
        await manager.stop_keepalive("conn-1")

        assert send_ping.await_count >= 1


class TestSubscriptionManagerDisconnect:
    @pytest.mark.asyncio
    async def test_disconnect_stops_keepalive(self) -> None:
        manager = SubscriptionManager(keepalive_interval=60.0)
        send_ping = AsyncMock()

        await manager.start_keepalive("conn-1", send_ping)
        assert "conn-1" in manager._keepalive_tasks

        await manager.disconnect("conn-1")

        assert "conn-1" not in manager._keepalive_tasks
