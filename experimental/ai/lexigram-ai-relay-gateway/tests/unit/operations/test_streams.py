"""Tests for the relay stream session registry."""

from __future__ import annotations

import asyncio

import pytest

from lexigram.ai.relay.gateway.operations.streams import RelayStreamRegistry


@pytest.fixture
def registry() -> RelayStreamRegistry:
    """A fresh empty registry."""
    return RelayStreamRegistry()


class TestRelayStreamRegistry:
    async def test_register_returns_id_and_clear_handle(
        self, registry: RelayStreamRegistry
    ) -> None:
        stream_id, handle = registry.register(
            channel="claude", model="sonnet", request_id="req-1"
        )
        assert stream_id
        assert isinstance(handle, asyncio.Event)
        assert not handle.is_set()

    async def test_registered_stream_is_listed(
        self, registry: RelayStreamRegistry
    ) -> None:
        stream_id, _ = registry.register(
            channel="claude", model="sonnet", request_id="req-1"
        )
        (active,) = registry.list()
        assert active.stream_id == stream_id
        assert active.channel == "claude"
        assert active.model == "sonnet"
        assert active.request_id == "req-1"
        assert active.started_at.tzinfo is not None

    async def test_unregister_removes_stream(
        self, registry: RelayStreamRegistry
    ) -> None:
        stream_id, _ = registry.register(
            channel="claude", model="sonnet", request_id="req-1"
        )
        registry.unregister(stream_id)
        assert registry.list() == ()
        assert registry.handle(stream_id) is None

    async def test_list_is_fifo(self, registry: RelayStreamRegistry) -> None:
        first, _ = registry.register(
            channel="claude", model="sonnet", request_id="req-1"
        )
        second, _ = registry.register(channel="gemini", model="pro", request_id="req-2")
        assert [s.stream_id for s in registry.list()] == [first, second]

    async def test_handle_for_unknown_stream_is_none(
        self, registry: RelayStreamRegistry
    ) -> None:
        assert registry.handle("ghost") is None

    async def test_cancel_sets_handle(self, registry: RelayStreamRegistry) -> None:
        stream_id, handle = registry.register(
            channel="claude", model="sonnet", request_id="req-1"
        )
        assert registry.cancel(stream_id) is True
        assert handle.is_set()

    async def test_cancel_unknown_stream_returns_false(
        self, registry: RelayStreamRegistry
    ) -> None:
        assert registry.cancel("ghost") is False

    async def test_cancelled_stream_stays_listed_until_unregister(
        self, registry: RelayStreamRegistry
    ) -> None:
        stream_id, _ = registry.register(
            channel="claude", model="sonnet", request_id="req-1"
        )
        registry.cancel(stream_id)
        assert len(registry.list()) == 1
