"""Tests for event streaming publisher functionality.

This module is skipped because the event streaming publisher implementation
has been removed from the codebase.
"""

import pytest

pytest.skip("streaming publisher removed", allow_module_level=True)

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

pytest_asyncio: Any = None
try:
    import pytest_asyncio
except ImportError:
    pytest_asyncio = None

from lexigram.events.messages.event import Event
from lexigram.events.streaming.publisher import EventPublisher


class TestEventPublisher:
    """Test EventPublisher functionality"""

    @pytest.fixture
    async def publisher(self):
        """Publisher fixture that ensures cleanup"""
        publisher = EventPublisher()
        yield publisher
        # Cleanup
        if hasattr(publisher, "_processing_task") and publisher._processing_task:
            publisher._processing_task.cancel()

    def test_publisher_initialization(self, publisher):
        """Test publisher initialization"""
        assert (
            publisher._subscribers == {}
        )  # Check internal state if public API is missing
        assert not publisher._global_subscribers

    @pytest.mark.asyncio
    async def test_publish_event(self, publisher):
        """Test publishing an event"""
        handler = MagicMock()
        publisher.subscribe_all(handler)

        event = Event(
            aggregate_id=uuid4(),
            event_type="test_event",
            data={"key": "value"},
        )

        # publish is awaitable
        count = await publisher.publish(event)

        assert count == 1
        handler.assert_called_once_with(event)

    def test_subscribe(self, publisher):
        """Test subscribing to events"""
        handler = MagicMock()

        class TestEvent(Event):
            pass

        sub_id = publisher.subscribe(TestEvent, handler)

        assert isinstance(sub_id, str)
        assert TestEvent in publisher._subscribers
        assert handler in publisher._subscribers[TestEvent]
        assert sub_id in publisher._subscriptions
        assert publisher._subscriptions[sub_id] == (TestEvent, handler)

    def test_subscribe_all(self, publisher):
        """Test subscribing to all events"""
        handler = MagicMock()

        sub_id = publisher.subscribe_all(handler)

        assert isinstance(sub_id, str)
        assert handler in publisher._global_subscribers
        assert sub_id in publisher._subscriptions
        assert publisher._subscriptions[sub_id] == (None, handler)

    def test_unsubscribe_by_id(self, publisher):
        """Test unsubscribing by ID"""
        handler = MagicMock()
        sub_id = publisher.subscribe_all(handler)

        assert sub_id in publisher._subscriptions

        result = publisher.unsubscribe(sub_id)

        assert result is True
        assert sub_id not in publisher._subscriptions
        assert handler not in publisher._global_subscribers

    def test_unsubscribe_by_type_and_handler(self, publisher):
        """Test unsubscribing by type and handler"""
        handler = MagicMock()

        class TestEvent(Event):
            pass

        publisher.subscribe(TestEvent, handler)

        result = publisher.unsubscribe(TestEvent, handler)

        assert result is True
        assert handler not in publisher._subscribers[TestEvent]

    @pytest.mark.asyncio
    async def test_publish_to_specific_subscriber(self, publisher):
        """Test publishing to specific subscriber"""
        handler = MagicMock()

        class TestEventA(Event):
            pass

        class TestEventB(Event):
            pass

        publisher.subscribe(TestEventA, handler)

        event_a = TestEventA(aggregate_id=uuid4(), event_type="TestEventA")
        event_b = TestEventB(aggregate_id=uuid4(), event_type="TestEventB")

        await publisher.publish(event_a)
        await publisher.publish(event_b)

        # handler should only receive event_a
        handler.assert_called_once_with(event_a)

    @pytest.mark.asyncio
    async def test_publish_with_async_handler(self, publisher):
        """Test publishing with async handler"""
        handler = AsyncMock()

        publisher.subscribe_all(handler)

        event = Event(aggregate_id=uuid4(), event_type="test")
        await publisher.publish(event)

        handler.assert_called_once_with(event)
