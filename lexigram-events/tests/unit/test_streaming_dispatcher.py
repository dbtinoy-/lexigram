"""Tests for events streaming dispatcher module."""

import pytest
from unittest.mock import AsyncMock

from lexigram.events.streaming.dispatcher import StreamDispatcher, DispatcherStats
from lexigram.events.messages.event import Event


class FakeEvent(Event):
    """Fake event for testing."""
    
    pass


class AnotherEvent(Event):
    """Another fake event for testing."""
    pass


class TestDispatcherStats:
    def test_dispatcher_stats_defaults(self) -> None:
        stats = DispatcherStats()
        assert stats.events_published == 0
        assert stats.events_failed == 0
        assert stats.active_subscribers == 0
        assert stats.last_event_at is None

    def test_dispatcher_stats_with_values(self) -> None:
        from datetime import datetime, UTC
        stats = DispatcherStats(
            events_published=10,
            events_failed=2,
            active_subscribers=5,
            last_event_at=datetime.now(UTC),
        )
        assert stats.events_published == 10
        assert stats.events_failed == 2
        assert stats.active_subscribers == 5


class TestStreamDispatcher:
    def test_dispatcher_initialization(self) -> None:
        dispatcher = StreamDispatcher()
        assert dispatcher._parallel_delivery is True
        assert dispatcher._continue_on_error is True
        assert dispatcher.stats.active_subscribers == 0

    def test_subscribe_specific_event(self) -> None:
        dispatcher = StreamDispatcher()
        
        async def handler(event: Event) -> None:
            pass
        
        sub_id = dispatcher.subscribe(FakeEvent, handler)
        assert sub_id is not None
        assert dispatcher.stats.active_subscribers == 1

    def test_subscribe_global(self) -> None:
        dispatcher = StreamDispatcher()
        
        async def handler(event: Event) -> None:
            pass
        
        sub_id = dispatcher.subscribe("*", handler)
        assert sub_id is not None
        assert dispatcher.stats.active_subscribers == 1

    def test_subscribe_all(self) -> None:
        dispatcher = StreamDispatcher()
        
        async def handler(event: Event) -> None:
            pass
        
        sub_id = dispatcher.subscribe_all(handler)
        assert sub_id is not None
        assert dispatcher.stats.active_subscribers == 1

    def test_unsubscribe_by_id(self) -> None:
        dispatcher = StreamDispatcher()
        
        async def handler(event: Event) -> None:
            pass
        
        sub_id = dispatcher.subscribe(FakeEvent, handler)
        result = dispatcher.unsubscribe(sub_id)
        assert result is True
        assert dispatcher.stats.active_subscribers == 0

    def test_unsubscribe_by_event_type(self) -> None:
        dispatcher = StreamDispatcher()
        
        async def handler(event: Event) -> None:
            pass
        
        dispatcher.subscribe(FakeEvent, handler)
        result = dispatcher.unsubscribe(FakeEvent, handler)
        assert result is True
        assert dispatcher.stats.active_subscribers == 0

    @pytest.mark.asyncio
    async def test_publish_no_subscribers(self) -> None:
        dispatcher = StreamDispatcher()
        event = FakeEvent()
        count = await dispatcher.publish(event)
        assert count == 0

    @pytest.mark.asyncio
    async def test_publish_with_subscriber(self) -> None:
        dispatcher = StreamDispatcher()
        received = []
        
        async def handler(event: Event) -> None:
            received.append(event)
        
        dispatcher.subscribe(FakeEvent, handler)
        event = FakeEvent()
        count = await dispatcher.publish(event)
        assert count == 1
        assert len(received) == 1
        assert dispatcher.stats.events_published == 1

    @pytest.mark.asyncio
    async def test_publish_batch(self) -> None:
        dispatcher = StreamDispatcher()
        
        async def handler(event: Event) -> None:
            pass
        
        dispatcher.subscribe(FakeEvent, handler)
        events = [FakeEvent(), FakeEvent(), FakeEvent()]
        count = await dispatcher.publish_batch(events)
        assert count == 3

    @pytest.mark.asyncio
    async def test_publish_inherits_parent_type(self) -> None:
        dispatcher = StreamDispatcher()
        received = []
        
        async def handler(event: Event) -> None:
            received.append(event)
        
        dispatcher.subscribe(Event, handler)
        event = FakeEvent()
        count = await dispatcher.publish(event)
        assert count == 1

    def test_stats_property(self) -> None:
        dispatcher = StreamDispatcher()
        stats = dispatcher.stats
        assert stats is not None
        assert isinstance(stats, DispatcherStats)
