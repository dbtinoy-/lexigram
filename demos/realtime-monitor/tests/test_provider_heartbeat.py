"""Unit tests for heartbeat task supervision in RealtimeProvider."""

from __future__ import annotations

import asyncio

import pytest

from ops_console.di.provider import RealtimeProvider
from ops_console.domain import SystemEvent


@pytest.mark.asyncio
async def test_heartbeat_survives_publish_crash_and_keeps_beating() -> None:
    provider = RealtimeProvider(heartbeat_interval=0.01)
    calls = {"count": 0}
    original_publish = provider.events.publish

    async def flaky_publish(event: SystemEvent) -> int:
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("simulated publish crash")
        return await original_publish(event)

    provider.events.publish = flaky_publish  # type: ignore[method-assign]

    provider._start_heartbeat()
    await asyncio.sleep(0.15)

    try:
        # First tick crashed; supervision must have restarted the loop and
        # subsequent ticks must keep publishing.
        assert calls["count"] >= 3
    finally:
        await provider.shutdown()


@pytest.mark.asyncio
async def test_shutdown_cancels_heartbeat_cleanly() -> None:
    provider = RealtimeProvider(heartbeat_interval=0.01)
    provider._start_heartbeat()
    await asyncio.sleep(0.05)

    await provider.shutdown()

    assert provider._heartbeat_task is None
