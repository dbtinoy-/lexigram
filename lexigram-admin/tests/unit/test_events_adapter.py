"""Tests for events adapter delegating to lexigram-events."""

from __future__ import annotations

import pytest

from lexigram.admin.events.adapter import AdminEventBusAdapter


class _FakeHandler:
    def __init__(self) -> None:
        self.calls: list[object] = []

    async def __call__(self, event: object) -> None:
        self.calls.append(event)


class TestAdminEventBusAdapter:
    @pytest.mark.asyncio
    async def test_publish_dispatches_to_subscriber(self) -> None:
        bus = AdminEventBusAdapter(event_bus=None)
        handler = _FakeHandler()
        bus.subscribe("TestEvent", handler)

        # With the internal _SimpleDispatcher, pub/sub works
        class TestEvent:
            pass

        await bus.publish(TestEvent())
        assert len(handler.calls) == 1

    @pytest.mark.asyncio
    async def test_publish_many_dispatches_all(self) -> None:
        bus = AdminEventBusAdapter(event_bus=None)
        handler = _FakeHandler()
        bus.subscribe("EventA", handler)

        class EventA:
            pass

        results = await bus.publish_many([EventA(), EventA()])
        assert len(results) == 2
        assert len(handler.calls) == 2

    @pytest.mark.asyncio
    async def test_publish_with_real_bus_delegates(self) -> None:
        from unittest.mock import AsyncMock

        mock_bus = AsyncMock()
        mock_bus.publish = AsyncMock(return_value="ok")
        bus = AdminEventBusAdapter(event_bus=mock_bus)

        result = await bus.publish("event")
        assert result == "ok"
        mock_bus.publish.assert_awaited_once_with("event")

    @pytest.mark.asyncio
    async def test_subscribe_delegates_to_real_bus(self) -> None:
        from unittest.mock import MagicMock

        mock_bus = MagicMock()
        bus = AdminEventBusAdapter(event_bus=mock_bus)

        handler = _FakeHandler()
        bus.subscribe("MyEvent", handler)
        mock_bus.subscribe.assert_called_once_with("MyEvent", handler)

    @pytest.mark.asyncio
    async def test_publish_many_with_real_bus(self) -> None:
        from unittest.mock import AsyncMock

        mock_bus = AsyncMock()
        mock_bus.publish = AsyncMock(return_value="ok")
        bus = AdminEventBusAdapter(event_bus=mock_bus)

        results = await bus.publish_many(["a", "b"])
        assert results == ["ok", "ok"]
        assert mock_bus.publish.await_count == 2

    @pytest.mark.asyncio
    async def test_publish_returns_none_on_exception(self) -> None:
        from unittest.mock import AsyncMock

        mock_bus = AsyncMock()
        mock_bus.publish = AsyncMock(side_effect=RuntimeError("fail"))
        bus = AdminEventBusAdapter(event_bus=mock_bus)

        result = await bus.publish("boom")
        assert result is None

    @pytest.mark.asyncio
    async def test_publish_many_with_exception_continues(self) -> None:
        from unittest.mock import AsyncMock

        mock_bus = AsyncMock()
        mock_bus.publish = AsyncMock(
            side_effect=[RuntimeError("fail"), "ok"],
        )
        bus = AdminEventBusAdapter(event_bus=mock_bus)

        results = await bus.publish_many(["a", "b"])
        assert results == [None, "ok"]
