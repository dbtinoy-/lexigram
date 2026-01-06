"""Tests for events protocol definitions."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.contracts.events.protocols import (
    AggregateFactoryProtocol,
    CommandBusProtocol,
    CommandHandlerProtocol,
    DomainEventPublisherProtocol,
    EventBusProtocol,
    EventHandlerProtocol,
    EventMiddlewareProtocol,
    EventSourcedReadRepositoryProtocol,
    EventSourcedRepositoryProtocol,
    EventStoreProtocol,
    IntegrationEventProtocol,
    MultiEventHandlerProtocol,
    ProjectionProtocol,
    PubSubProtocol,
    QueryBusProtocol,
    QueryHandlerProtocol,
    SnapshotStoreProtocol,
    WebhookSignatureVerifierProtocol,
)


class TestDomainEventPublisherProtocol:
    """Tests for DomainEventPublisherProtocol."""

    @pytest.mark.asyncio
    async def test_has_publish_method(self) -> None:
        """Test protocol has publish async method."""

        class Publisher:
            async def publish(self, event: Any) -> None:
                pass

        publisher = Publisher()
        await publisher.publish({"event": "test"})

    def test_is_runtime_checkable(self) -> None:
        """Test protocol is runtime checkable."""

        class Publisher:
            async def publish(self, event: Any) -> None:
                pass

        assert isinstance(Publisher(), DomainEventPublisherProtocol)


class TestEventHandlerProtocol:
    """Tests for EventHandlerProtocol."""

    @pytest.mark.asyncio
    async def test_has_handle_method(self) -> None:
        """Test protocol has handle async method."""

        from lexigram.result import Ok

        class Handler:
            async def handle(self, event: Any) -> Any:
                return Ok(None)

        handler = Handler()
        result = await handler.handle({"event": "test"})
        assert result.is_ok()

    def test_is_runtime_checkable(self) -> None:
        """Test protocol is runtime checkable."""

        from lexigram.result import Ok

        class Handler:
            async def handle(self, event: Any) -> Any:
                return Ok(None)

        assert isinstance(Handler(), EventHandlerProtocol)


class TestMultiEventHandlerProtocol:
    """Tests for MultiEventHandlerProtocol."""

    def test_has_handles_method(self) -> None:
        """Test protocol has handles method."""

        class Handler:
            def handles(self) -> list[type]:
                return [type("Event1", (), {}), type("Event2", (), {})]

        handler = Handler()
        result = handler.handles()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_has_handle_method(self) -> None:
        """Test protocol has handle async method."""

        from lexigram.result import Ok

        class Handler:
            def handles(self) -> list[type]:
                return []

            async def handle(self, event: Any) -> Any:
                return Ok(None)

        handler = Handler()
        result = await handler.handle({"event": "test"})
        assert result.is_ok()

    def test_is_runtime_checkable(self) -> None:
        """Test protocol is runtime checkable."""

        from lexigram.result import Ok

        class Handler:
            def handles(self) -> list[type]:
                return []

            async def handle(self, event: Any) -> Any:
                return Ok(None)

        assert isinstance(Handler(), MultiEventHandlerProtocol)


class TestEventBusProtocol:
    """Tests for EventBusProtocol."""

    @pytest.mark.asyncio
    async def test_has_publish_method(self) -> None:
        """Test protocol has publish async method."""

        from lexigram.result import Ok

        class Bus:
            async def publish(self, event: Any) -> Any:
                return Ok(None)

        bus = Bus()
        result = await bus.publish({"event": "test"})
        assert result.is_ok()

    def test_has_subscribe_method(self) -> None:
        """Test protocol has subscribe method."""

        def dummy_handler(e: Any) -> None:
            pass

        class Bus:
            def subscribe(self, event_type: type, handler: Any) -> None:
                pass

        bus = Bus()
        bus.subscribe(type("Event", (), {}), dummy_handler)

    def test_has_unsubscribe_method(self) -> None:
        """Test protocol has unsubscribe method."""

        def dummy_handler(e: Any) -> None:
            pass

        class Bus:
            def unsubscribe(self, event_type: type, handler: Any) -> None:
                pass

        bus = Bus()
        bus.unsubscribe(type("Event", (), {}), dummy_handler)

    def test_is_runtime_checkable(self) -> None:
        """Test protocol is runtime checkable."""

        from lexigram.result import Ok

        class Bus:
            async def publish(self, event: Any) -> Any:
                return Ok(None)

            def subscribe(self, event_type: type, handler: Any) -> None:
                pass

            def unsubscribe(self, event_type: type, handler: Any) -> None:
                pass

        assert isinstance(Bus(), EventBusProtocol)


class TestEventMiddlewareProtocol:
    """Tests for EventMiddlewareProtocol."""

    @pytest.mark.asyncio
    async def test_has_call_method(self) -> None:
        """Test protocol has __call__ async method."""

        async def noop_next(event: Any) -> None:
            pass

        class Middleware:
            async def __call__(self, event: Any, next_handler: Any) -> None:
                pass

        middleware = Middleware()
        await middleware({"event": "test"}, noop_next)

    def test_is_runtime_checkable(self) -> None:
        """Test protocol is runtime checkable."""

        class Middleware:
            async def __call__(self, event: Any, next_handler: Any) -> None:
                pass

        assert isinstance(Middleware(), EventMiddlewareProtocol)


class TestCommandHandlerProtocol:
    """Tests for CommandHandlerProtocol."""

    @pytest.mark.asyncio
    async def test_has_handle_method(self) -> None:
        """Test protocol has handle async method."""

        class Handler:
            async def handle(self, command: Any) -> Any:
                return {"status": "handled"}

        handler = Handler()
        result = await handler.handle({"command": "test"})
        assert result["status"] == "handled"

    def test_is_runtime_checkable(self) -> None:
        """Test protocol is runtime checkable."""

        class Handler:
            async def handle(self, command: Any) -> Any:
                return {}

        assert isinstance(Handler(), CommandHandlerProtocol)


class TestCommandBusProtocol:
    """Tests for CommandBusProtocol."""

    @pytest.mark.asyncio
    async def test_has_dispatch_method(self) -> None:
        """Test protocol has dispatch async method."""

        class Bus:
            async def dispatch(self, command: Any) -> Any:
                return {"status": "dispatched"}

        bus = Bus()
        result = await bus.dispatch({"command": "test"})
        assert result["status"] == "dispatched"

    def test_is_runtime_checkable(self) -> None:
        """Test protocol is runtime checkable."""

        class Bus:
            async def dispatch(self, command: Any) -> Any:
                return {}

        assert isinstance(Bus(), CommandBusProtocol)


class TestQueryHandlerProtocol:
    """Tests for QueryHandlerProtocol."""

    @pytest.mark.asyncio
    async def test_has_handle_method(self) -> None:
        """Test protocol has handle async method."""

        class Handler:
            async def handle(self, query: Any) -> Any:
                return {"data": "test"}

        handler = Handler()
        result = await handler.handle({"query": "test"})
        assert result["data"] == "test"

    def test_is_runtime_checkable(self) -> None:
        """Test protocol is runtime checkable."""

        class Handler:
            async def handle(self, query: Any) -> Any:
                return {}

        assert isinstance(Handler(), QueryHandlerProtocol)


class TestQueryBusProtocol:
    """Tests for QueryBusProtocol."""

    @pytest.mark.asyncio
    async def test_has_execute_method(self) -> None:
        """Test protocol has execute async method."""

        class Bus:
            async def execute(self, query: Any) -> Any:
                return {"data": "test"}

        bus = Bus()
        result = await bus.execute({"query": "test"})
        assert result["data"] == "test"

    def test_is_runtime_checkable(self) -> None:
        """Test protocol is runtime checkable."""

        class Bus:
            async def execute(self, query: Any) -> Any:
                return {}

        assert isinstance(Bus(), QueryBusProtocol)


class TestEventStoreProtocol:
    """Tests for EventStoreProtocol."""

    @pytest.mark.asyncio
    async def test_has_append_method(self) -> None:
        """Test protocol has append async method."""

        class Store:
            async def append(
                self,
                stream_id: str,
                events: list[Any],
                expected_version: int | None = None,
            ) -> int:
                return 1

        store = Store()
        version = await store.append("stream-1", [{"event": "test"}])
        assert version == 1

    @pytest.mark.asyncio
    async def test_has_read_method(self) -> None:
        """Test protocol has read async method."""

        class Store:
            async def read(
                self,
                stream_id: str,
                start: int = 0,
                count: int | None = None,
            ) -> list[Any]:
                return [{"event": "test"}]

        store = Store()
        events = await store.read("stream-1")
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_has_read_all_method(self) -> None:
        """Test protocol has read_all async method."""

        class Store:
            async def read_all(
                self,
                position: int = 0,
                count: int | None = None,
            ) -> list[Any]:
                return []

        store = Store()
        events = await store.read_all()
        assert isinstance(events, list)

    def test_is_runtime_checkable(self) -> None:
        """Test protocol is runtime checkable."""

        class Store:
            async def append(self, stream_id: str, events: list, **kwargs: Any) -> int:
                return 0

            async def read(self, stream_id: str, **kwargs: Any) -> list:
                return []

            async def read_all(self, **kwargs: Any) -> list:
                return []

        assert isinstance(Store(), EventStoreProtocol)


class TestSnapshotStoreProtocol:
    """Tests for SnapshotStoreProtocol."""

    @pytest.mark.asyncio
    async def test_has_save_method(self) -> None:
        """Test protocol has save async method."""

        class Store:
            async def save(self, aggregate_id: str, snapshot: Any, version: int) -> None:
                pass

        store = Store()
        await store.save("agg-1", {"state": "test"}, 1)

    @pytest.mark.asyncio
    async def test_has_load_method(self) -> None:
        """Test protocol has load async method."""

        class Store:
            async def load(self, aggregate_id: str) -> tuple[Any, int] | None:
                return ({"state": "test"}, 1)

        store = Store()
        result = await store.load("agg-1")
        assert result is not None

    def test_is_runtime_checkable(self) -> None:
        """Test protocol is runtime checkable."""

        class Store:
            async def save(self, aggregate_id: str, snapshot: Any, version: int) -> None:
                pass

            async def load(self, aggregate_id: str) -> tuple | None:
                return None

        assert isinstance(Store(), SnapshotStoreProtocol)


class TestEventSourcedReadRepositoryProtocol:
    """Tests for EventSourcedReadRepositoryProtocol."""

    @pytest.mark.asyncio
    async def test_has_get_method(self) -> None:
        """Test protocol has get async method."""

        class Repo:
            async def get(self, aggregate_id: Any) -> Any | None:
                return {"id": aggregate_id}

        repo = Repo()
        result = await repo.get("agg-1")
        assert result["id"] == "agg-1"

    @pytest.mark.asyncio
    async def test_has_exists_method(self) -> None:
        """Test protocol has exists async method."""

        class Repo:
            async def exists(self, aggregate_id: Any) -> bool:
                return True

        repo = Repo()
        result = await repo.exists("agg-1")
        assert result is True

    @pytest.mark.asyncio
    async def test_has_get_all_method(self) -> None:
        """Test protocol has get_all async method."""

        class Repo:
            async def get_all(
                self,
                limit: int | None = None,
                offset: int | None = None,
            ) -> list[Any]:
                return []

        repo = Repo()
        result = await repo.get_all()
        assert isinstance(result, list)

    def test_is_runtime_checkable(self) -> None:
        """Test protocol is runtime checkable."""

        class Repo:
            async def get(self, aggregate_id: Any) -> Any | None:
                return None

            async def exists(self, aggregate_id: Any) -> bool:
                return False

            async def get_all(self, **kwargs: Any) -> list:
                return []

        assert isinstance(Repo(), EventSourcedReadRepositoryProtocol)


class TestEventSourcedRepositoryProtocol:
    """Tests for EventSourcedRepositoryProtocol."""

    def test_protocol_extends_read_repo(self) -> None:
        """Test protocol extends EventSourcedReadRepositoryProtocol."""
        assert issubclass(EventSourcedRepositoryProtocol, EventSourcedReadRepositoryProtocol)


class TestAggregateFactoryProtocol:
    """Tests for AggregateFactoryProtocol."""

    def test_factory_returns_aggregate(self) -> None:
        class Factory:
            def create(self, aggregate_id: UUID | str) -> Any:
                return "aggregate"

        assert isinstance(Factory(), AggregateFactoryProtocol)


class TestProjectionProtocol:
    """Tests for ProjectionProtocol."""

    def test_has_apply_method(self) -> None:
        """Test protocol has apply method."""

        class Projection:
            def apply(self, event: Any) -> None:
                pass

        projection = Projection()
        projection.apply({"event": "test"})

    def test_is_runtime_checkable(self) -> None:
        """Test protocol is runtime checkable."""

        class Projection:
            def apply(self, event: Any) -> None:
                pass

        assert isinstance(Projection(), ProjectionProtocol)


class TestPubSubProtocol:
    """Tests for PubSubProtocol."""

    @pytest.mark.asyncio
    async def test_has_publish_method(self) -> None:
        """Test protocol has publish async method."""

        class PubSub:
            async def publish(self, topic: str, data: Any) -> None:
                pass

        pubsub = PubSub()
        await pubsub.publish("topic1", {"data": "test"})

    @pytest.mark.asyncio
    async def test_has_subscribe_method(self) -> None:
        """Test protocol has subscribe async method."""

        class PubSub:
            async def subscribe(
                self,
                topic: str,
                handler: Any,
            ) -> None:
                pass

        pubsub = PubSub()
        await pubsub.subscribe("topic1", lambda: None)

    @pytest.mark.asyncio
    async def test_has_unsubscribe_method(self) -> None:
        """Test protocol has unsubscribe async method."""

        class PubSub:
            async def unsubscribe(self, topic: str, handler: Any) -> None:
                pass

        pubsub = PubSub()
        await pubsub.unsubscribe("topic1", lambda: None)

    def test_is_runtime_checkable(self) -> None:
        """Test protocol is runtime checkable."""

        class PubSub:
            async def publish(self, topic: str, data: Any) -> None:
                pass

            async def subscribe(self, topic: str, handler: Any) -> None:
                pass

            async def unsubscribe(self, topic: str, handler: Any) -> None:
                pass

        assert isinstance(PubSub(), PubSubProtocol)


class TestIntegrationEventProtocol:
    """Tests for IntegrationEventProtocol."""

    def test_has_required_attributes(self) -> None:
        """Test protocol has required attributes."""

        class Event:
            event_id: str = "evt-1"
            event_type: str = "TestEvent"
            source_service: str = "test-service"
            correlation_id: str | None = None
            causation_id: str | None = None
            payload: dict[str, Any] = {}
            occurred_at: Any = None

        event = Event()
        assert event.event_id == "evt-1"
        assert event.event_type == "TestEvent"

    def test_is_runtime_checkable(self) -> None:
        """Test protocol is runtime checkable."""

        class Event:
            event_id: str = ""
            event_type: str = ""
            source_service: str = ""
            correlation_id: str | None = None
            causation_id: str | None = None
            payload: dict = {}
            occurred_at: Any = None

        assert isinstance(Event(), IntegrationEventProtocol)


class TestWebhookSignatureVerifierProtocol:
    """Tests for WebhookSignatureVerifierProtocol."""

    def test_has_verify_method(self) -> None:
        """Test protocol has verify method."""

        class Verifier:
            def verify(
                self,
                payload: bytes,
                signature: str,
                secret: str,
            ) -> bool:
                return True

        verifier = Verifier()
        result = verifier.verify(b"payload", "signature", "secret")
        assert result is True

    def test_has_compute_signature_method(self) -> None:
        """Test protocol has compute_signature method."""

        class Verifier:
            def compute_signature(self, payload: bytes, secret: str) -> str:
                return "computed_signature"

        verifier = Verifier()
        result = verifier.compute_signature(b"payload", "secret")
        assert result == "computed_signature"

    def test_is_runtime_checkable(self) -> None:
        """Test protocol is runtime checkable."""

        class Verifier:
            def verify(self, payload: bytes, signature: str, secret: str) -> bool:
                return False

            def compute_signature(self, payload: bytes, secret: str) -> str:
                return ""

        assert isinstance(Verifier(), WebhookSignatureVerifierProtocol)
