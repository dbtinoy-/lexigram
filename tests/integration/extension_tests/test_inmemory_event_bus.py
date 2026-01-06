import pytest

from lexigram.contracts.domain import DomainEvent
from lexigram.testing.memory.event_bus import InMemoryEventBus


class MyEvent(DomainEvent):
    payload: str


class Handler:
    def __init__(self):
        self.called_with: list[MyEvent] = []

    async def handle(self, event: MyEvent) -> None:
        self.called_with.append(event)


@pytest.mark.asyncio
async def test_inmemory_event_bus_basic():
    bus = InMemoryEventBus()
    handler = Handler()
    bus.subscribe(MyEvent, handler)

    event = MyEvent(payload="hello")
    await bus.publish(event)

    assert handler.called_with == [event]


@pytest.mark.asyncio
async def test_inmemory_event_bus_multiple_handlers():
    bus = InMemoryEventBus()

    results: list[str] = []

    async def h1(evt: MyEvent):
        results.append("h1:" + evt.payload)

    async def h2(evt: MyEvent):
        results.append("h2:" + evt.payload)

    bus.subscribe(MyEvent, h1)
    bus.subscribe(MyEvent, h2)

    await bus.publish(MyEvent(payload="x"))

    assert "h1:x" in results
    assert "h2:x" in results


@pytest.mark.asyncio
async def test_inmemory_event_bus_wildcard():
    """Handlers registered with "*" get every event regardless of type."""

    class OtherEvent(DomainEvent):
        value: int

    bus = InMemoryEventBus()
    wildcard_results: list[str] = []

    async def wildcard_handler(evt: DomainEvent):
        wildcard_results.append(evt.__class__.__name__)

    # subscribe wildcard and a normal handler
    bus.subscribe("*", wildcard_handler, priority=5)
    handler = Handler()
    bus.subscribe(MyEvent, handler, priority=10)

    e1 = MyEvent(payload="foo")
    e2 = OtherEvent(value=42)
    await bus.publish(e1)
    await bus.publish(e2)

    assert wildcard_results == ["MyEvent", "OtherEvent"]
    assert handler.called_with == [e1]

    # counts should include wildcard but not list it in types
    assert bus.subscriber_count == 2
    assert bus.subscribed_types == {MyEvent}

    # unsubscribe wildcard and ensure it stops receiving
    bus.unsubscribe("*", wildcard_handler)
    wildcard_results.clear()
    await bus.publish(MyEvent(payload="bar"))
    assert wildcard_results == []
