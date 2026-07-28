"""Unit tests for lexigram-events buses"""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from lexigram.contracts.domain import DomainEvent
from lexigram.events.buses import (
    CommandBusImpl,
    EventBusImpl,
    QueryBusImpl,
)
from lexigram.events.buses.base import Bus, HandlerNotFoundError
from lexigram.events.buses.command import CommandExecutionError
from lexigram.events.buses.event import EventHandlerError
from lexigram.events.buses.query import QueryExecutionError
from lexigram.events.decorators import (
    command_handler,
    event_handler,
    query_handler,
)
from lexigram.events.hooks import EventHandledHook, EventPublishedHook
from lexigram.events.messages import Command, Event, Query
from lexigram.hooks import HookRegistry

# Ensure helper `make_domain_event` is available in varied test invocation contexts
try:
    from lexigram.events.tests.unit.conftest import make_domain_event
except ImportError:
    try:
        from tests.conftest import make_domain_event
    except ImportError:

        def make_domain_event(**kwargs):
            from uuid import uuid4

            from lexigram.contracts.domain import DomainEvent

            data = {
                "aggregate_id": kwargs.get("aggregate_id", uuid4()),
                "aggregate_type": kwargs.get("aggregate_type", "TestAggregate"),
                "event_type": kwargs.get("event_type", None),
                "sequence_number": kwargs.get("sequence_number", kwargs.get("version", 0)),
                "actor_id": kwargs.get("actor_id", None),
            }
            data.update(kwargs)
            if "version" in data:
                del data["version"]
            return DomainEvent(**data)


class TestCommandBus:
    """Test CommandBusProtocol"""

    def test_command_bus_creation(self):
        """Test command bus creation"""
        bus = CommandBusImpl()
        assert bus._middlewares == []
        assert bus._handlers == {}

    @pytest.mark.asyncio
    async def test_command_send(self):
        """Test command sending"""
        bus = CommandBusImpl()
        command = Command()
        handler = AsyncMock()
        handler.return_value = "result"

        bus.register(Command, handler)

        result = await bus.dispatch(command)

        handler.assert_called_once_with(command)
        assert result == "result"

    def test_register_handler_type(self):
        """Test registering handler type"""
        bus = CommandBusImpl()

        class TestHandler:
            pass

        bus.register(Command, TestHandler)
        assert bus._handlers[Command] == TestHandler

    @pytest.mark.asyncio
    async def test_command_send_handler_not_found(self):
        """Test command sending with no handler found"""
        bus = CommandBusImpl()
        command = Command()

        with pytest.raises(HandlerNotFoundError) as exc_info:
            await bus.dispatch(command)

        assert "Command" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_command_send_handler_execution_error(self):
        """Test command sending with handler execution error"""
        bus = CommandBusImpl()
        command = Command()
        handler = AsyncMock()
        handler.side_effect = ValueError("Handler error")

        bus.register(Command, handler)

        with pytest.raises(CommandExecutionError) as exc_info:
            await bus.dispatch(command)

        assert exc_info.value.command_type == "Command"
        assert "Handler error" in exc_info.value.error

    @pytest.mark.asyncio
    async def test_command_send_preserves_known_errors(self):
        """Test command sending preserves HandlerNotFoundError and CommandExecutionError"""
        bus = CommandBusImpl()
        command = Command()
        handler = AsyncMock()
        handler.side_effect = CommandExecutionError("Command", "test error")

        bus.register(Command, handler)

        with pytest.raises(CommandExecutionError):
            await bus.dispatch(command)



    @pytest.mark.asyncio
    async def test_command_bus_explicit_handler_registration(self):
        """Test explicit handler registration works correctly"""
        bus = CommandBusImpl()

        class ExplicitHandler:
            pass

        bus.register(Command, ExplicitHandler)
        resolved = await bus._resolve_handler(Command)
        assert isinstance(resolved, ExplicitHandler)


class TestQueryBus:
    """Test QueryBusProtocol"""

    def test_query_bus_creation(self):
        """Test query bus creation"""
        bus = QueryBusImpl()
        assert bus._middlewares == []
        assert bus._handlers == {}

    @pytest.mark.asyncio
    async def test_query_send(self):
        """Test query sending"""
        bus = QueryBusImpl()
        query = Query()
        handler = AsyncMock()
        handler.return_value = "result"

        bus.register(Query, handler)

        result = await bus.execute(query)

        handler.assert_called_once_with(query)
        assert result == "result"

    def test_register_handler_type(self):
        """Test registering handler type"""
        bus = QueryBusImpl()

        class TestHandler:
            pass

        bus.register(Query, TestHandler)
        assert bus._handlers[Query] == TestHandler

    @pytest.mark.asyncio
    async def test_query_send_handler_not_found(self):
        """Test query sending with no handler found"""
        bus = QueryBusImpl()
        query = Query()

        with pytest.raises(HandlerNotFoundError) as exc_info:
            await bus.execute(query)

        assert "Query" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_query_send_handler_execution_error(self):
        """Test query sending with handler execution error"""
        bus = QueryBusImpl()
        query = Query()
        handler = AsyncMock()
        handler.side_effect = ValueError("Handler error")

        bus.register(Query, handler)

        with pytest.raises(QueryExecutionError) as exc_info:
            await bus.execute(query)

        assert exc_info.value.query_type == "Query"
        assert "Handler error" in exc_info.value.error

    @pytest.mark.asyncio
    async def test_query_send_preserves_known_errors(self):
        """Test query sending preserves HandlerNotFoundError and QueryExecutionError"""
        bus = QueryBusImpl()
        query = Query()
        handler = AsyncMock()
        handler.side_effect = QueryExecutionError("Query", "test error")

        bus.register(Query, handler)

        with pytest.raises(QueryExecutionError):
            await bus.execute(query)



    @pytest.mark.asyncio
    async def test_query_bus_explicit_handler_registration(self):
        """Test explicit handler registration works correctly"""
        bus = QueryBusImpl()

        class ExplicitHandler:
            pass

        bus.register(Query, ExplicitHandler)
        resolved = await bus._resolve_handler(Query)
        assert isinstance(resolved, ExplicitHandler)


class TestEventBus:
    """Test EventBusProtocol"""

    def test_event_bus_creation(self):
        """Test event bus creation"""
        bus = EventBusImpl()
        assert isinstance(bus, Bus)
        assert bus._subscribers == {}
        assert bus._global_handlers == []

    @pytest.mark.asyncio
    async def test_event_publish(self):
        """Test basic event publication"""
        bus = EventBusImpl()
        aggregate_id = uuid4()
        event = make_domain_event(aggregate_id=aggregate_id)
        handler = AsyncMock()

        bus.subscribe(DomainEvent, handler)

        await bus.publish(event)
        await bus.flush()  # wait for drain task to dispatch

        handler.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_event_publish_emits_event_published_hook(self):
        """Publishing emits the canonical ``event.published`` hook."""
        received: list[EventPublishedHook] = []
        registry = HookRegistry("events-test")

        async def capture(payload: EventPublishedHook) -> None:
            received.append(payload)

        registry.register_action("event.published", capture)

        bus = EventBusImpl(hooks=registry)
        event = make_domain_event(aggregate_id=uuid4())
        handler = AsyncMock()
        bus.subscribe(DomainEvent, handler)

        result = await bus.publish(event)
        await bus.flush()

        assert result.is_ok()
        assert received == [
            EventPublishedHook(
                event_type=f"{type(event).__module__}.{type(event).__qualname__}",
                aggregate_id=str(event.aggregate_id),
            )
        ]

    @pytest.mark.asyncio
    async def test_event_publish_emits_event_handled_hook_after_successful_handler(self):
        """Successful handlers emit ``event.handled`` once per handler."""
        received: list[EventHandledHook] = []
        registry = HookRegistry("events-test")

        async def capture(payload: EventHandledHook) -> None:
            received.append(payload)

        async def handler(event: DomainEvent) -> None:
            return None

        registry.register_action("event.handled", capture)

        bus = EventBusImpl(hooks=registry)
        event = make_domain_event(aggregate_id=uuid4())
        bus.subscribe(DomainEvent, handler)

        result = await bus.publish(event)
        await bus.flush()

        assert result.is_ok()
        assert received == [
            EventHandledHook(
                event_type=f"{type(event).__module__}.{type(event).__qualname__}",
                handler=f"{handler.__module__}.{handler.__qualname__}",
            )
        ]

    @pytest.mark.asyncio
    async def test_failed_handler_does_not_emit_event_handled_hook(self):
        """Failed handlers do not emit ``event.handled``."""
        received: list[EventHandledHook] = []
        registry = HookRegistry("events-test")

        async def capture(payload: EventHandledHook) -> None:
            received.append(payload)

        async def failing_handler(event: DomainEvent) -> None:
            raise ValueError("boom")

        registry.register_action("event.handled", capture)

        bus = EventBusImpl(hooks=registry)
        event = make_domain_event(aggregate_id=uuid4())
        bus.subscribe(DomainEvent, failing_handler)

        result = await bus.publish(event)
        await bus.flush()

        assert result.is_ok()
        assert received == []

    @pytest.mark.asyncio
    async def test_event_publish_no_handlers(self):
        """Test event publishing with no handlers"""
        bus = EventBusImpl()
        aggregate_id = uuid4()
        event = make_domain_event(aggregate_id=aggregate_id)

        # Should return None when no handlers
        await bus.publish(event)

    def test_subscribe_and_unsubscribe(self):
        """Test subscribing and unsubscribing handlers"""
        bus = EventBusImpl()
        handler = Mock()

        bus.subscribe(DomainEvent, handler)
        assert handler in bus._subscribers[DomainEvent]

        bus.unsubscribe(DomainEvent, handler)
        assert handler not in bus._subscribers[DomainEvent]

    def test_unsubscribe_nonexistent_handler(self):
        """Test unsubscribing a handler that doesn't exist"""
        bus = EventBusImpl()
        handler1 = Mock()
        handler2 = Mock()

        bus.subscribe(DomainEvent, handler1)
        # Try to unsubscribe handler2 which was never subscribed
        result = bus.unsubscribe(DomainEvent, handler2)
        assert result is False
        assert handler1 in bus._subscribers[DomainEvent]

    def test_subscribe_all(self):
        """Test subscribing to all events"""
        bus = EventBusImpl()
        handler = Mock()

        bus.subscribe_all(handler)
        assert handler in bus._global_handlers

    @pytest.mark.asyncio
    async def test_global_handler(self):
        """Test global event handler"""
        bus = EventBusImpl()
        aggregate_id = uuid4()
        event = make_domain_event(aggregate_id=aggregate_id)
        handler = AsyncMock()

        bus.subscribe_all(handler)

        await bus.publish(event)
        await bus.flush()  # wait for drain task to dispatch

        handler.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_event_publish_parallel_dispatch(self):
        """Test event publishing with parallel dispatch"""
        from lexigram.contracts.core import ExecutionStrategy
        from lexigram.concurrency import Parallel
        from lexigram.events.buses.event import EventBusConfig

        config = EventBusConfig(parallel_dispatch=True)
        bus = EventBusImpl(config=config)

        aggregate_id = uuid4()
        event = make_domain_event(aggregate_id=aggregate_id)
        handler1 = AsyncMock()
        handler2 = AsyncMock()

        bus.subscribe(DomainEvent, handler1)
        bus.subscribe(DomainEvent, handler2)

        async def mock_execute(*args, **kwargs):
            # Close coroutines to avoid warnings
            for aw in args:
                if hasattr(aw, "close"):
                    aw.close()
            return [(handler1, None), (handler2, None)]

        with patch.object(Parallel, "execute", side_effect=mock_execute) as mock_execute:
            await bus.publish(event)
            # flush() must be called inside the patch context so the drain
            # task runs while Parallel.execute is still mocked.
            await bus.flush()

        # Verify Parallel.execute was called with both handlers
        mock_execute.assert_called_once()
        args, kwargs = mock_execute.call_args
        assert len(args) == 2  # Two handler tasks
        assert kwargs["strategy"] == ExecutionStrategy.ALL_SETTLED

    @pytest.mark.asyncio
    async def test_event_publish_parallel_with_error_stop(self):
        """Test parallel event publishing records errors when continue_on_error=False.

        With channel-based dispatch, publish() returns immediately after enqueuing.
        Handler errors are collected in bus._dispatch_errors rather than raised
        synchronously from publish().
        """
        from lexigram.events.buses.event import EventBusConfig

        config = EventBusConfig(parallel_dispatch=True, continue_on_error=False, retry_failed_handlers=False)
        bus = EventBusImpl(config=config)

        aggregate_id = uuid4()
        event = make_domain_event(aggregate_id=aggregate_id)

        async def handler1(e):
            raise ValueError("handler1 failed")

        async def handler2(e):
            return None

        bus.subscribe(DomainEvent, handler1)
        bus.subscribe(DomainEvent, handler2)

        await bus.publish(event)
        await bus.flush()  # wait for drain task to process

        assert len(bus._dispatch_errors) == 1
        err = bus._dispatch_errors[0]
        assert isinstance(err, EventHandlerError)
        assert err.handler == handler1.__name__
        assert "handler1 failed" in err.error

    @pytest.mark.asyncio
    async def test_event_publish_parallel_with_error_continue(self):
        """Test parallel event publishing that continues on error"""
        from lexigram.events.buses.event import EventBusConfig

        config = EventBusConfig(parallel_dispatch=True, continue_on_error=True)
        bus = EventBusImpl(config=config)

        aggregate_id = uuid4()
        event = make_domain_event(aggregate_id=aggregate_id)

        async def handler1(e):
            raise ValueError("handler1 failed")

        handler2 = AsyncMock()

        bus.subscribe(DomainEvent, handler1)
        bus.subscribe(DomainEvent, handler2)

        await bus.publish(event)
        await bus.flush()  # wait for drain task to dispatch

        handler2.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_event_publish_sequential_with_error_continue(self):
        """Test sequential event publishing that continues on error"""
        from lexigram.events.buses.event import EventBusConfig

        config = EventBusConfig(continue_on_error=True, retry_failed_handlers=False)
        bus = EventBusImpl(config=config)

        aggregate_id = uuid4()
        event = make_domain_event(aggregate_id=aggregate_id)
        handler1 = AsyncMock()
        handler1.side_effect = ValueError("Handler 1 failed")
        handler2 = AsyncMock()

        bus.subscribe(DomainEvent, handler1)
        bus.subscribe(DomainEvent, handler2)

        await bus.publish(event)
        await bus.flush()  # wait for drain task to dispatch

        # Both handlers should have been called despite handler1 failing
        handler1.assert_called_once_with(event)
        handler2.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_event_publish_sequential_with_error_stop(self):
        """Test sequential event publishing stops on error and records it.

        With channel-based dispatch, publish() returns immediately after enqueuing.
        Handler errors are collected in bus._dispatch_errors rather than raised
        synchronously from publish().
        """
        from lexigram.events.buses.event import EventBusConfig

        config = EventBusConfig(parallel_dispatch=False, continue_on_error=False, retry_failed_handlers=False)
        bus = EventBusImpl(config=config)

        aggregate_id = uuid4()
        event = make_domain_event(aggregate_id=aggregate_id)
        handler1 = AsyncMock()
        handler1.__name__ = "handler1"
        handler1.side_effect = ValueError("Handler 1 failed")
        handler2 = AsyncMock()

        bus.subscribe(DomainEvent, handler1)
        bus.subscribe(DomainEvent, handler2)

        await bus.publish(event)
        await bus.flush()  # wait for drain task to process

        assert len(bus._dispatch_errors) == 1
        err = bus._dispatch_errors[0]
        assert isinstance(err, EventHandlerError)
        assert err.event_type == "DomainEvent"
        assert err.handler == "handler1"
        assert "Handler 1 failed" in err.error

        # Only handler1 should have been called (continue_on_error=False)
        handler1.assert_called_once_with(event)
        handler2.assert_not_called()

    @pytest.mark.asyncio
    async def test_event_inheritance_handlers(self):
        """Test that handlers for parent event types are called"""
        bus = EventBusImpl()

        class BaseEvent(Event):
            pass

        class DerivedEvent(BaseEvent):
            pass

        base_handler = AsyncMock()
        derived_handler = AsyncMock()

        bus.subscribe(BaseEvent, base_handler)
        bus.subscribe(DerivedEvent, derived_handler)

        event = DerivedEvent(aggregate_id=uuid4())
        await bus.publish(event)
        await bus.flush()  # wait for drain task to dispatch

        # Both handlers should be called
        base_handler.assert_called_once_with(event)
        derived_handler.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_event_publish_respects_concurrency_limit(self):
        """Test that event publishing respects the max_concurrent_handlers limit."""
        from lexigram.events.config import EventBusConfig
        import asyncio

        config = EventBusConfig(max_concurrent_handlers=2, parallel_dispatch=True)
        bus = EventBusImpl(config=config)
        aggregate_id = uuid4()
        event = make_domain_event(aggregate_id=aggregate_id)

        concurrent_count = 0
        max_seen = 0
        lock = asyncio.Lock()

        async def slow_handler(e):
            nonlocal concurrent_count, max_seen
            async with lock:
                concurrent_count += 1
                max_seen = max(max_seen, concurrent_count)
            await asyncio.sleep(0.01)
            async with lock:
                concurrent_count -= 1
            return "done"

        # Register 5 handlers
        for _ in range(5):
            bus.subscribe(DomainEvent, slow_handler)

        await bus.publish(event)
        await bus.flush()  # wait for drain task to dispatch all handlers

        assert max_seen == 2  # Should not exceed limit of 2



class TestDecorators:
    """Test handler decorators"""

    def test_command_handler_decorator(self):
        """Test command handler decorator"""
        bus = CommandBusImpl()

        @command_handler(Command)
        class TestCommandHandler:
            async def handle(self, cmd):
                return "handled"

        # The decorator should attach handler info
        from lexigram.events.decorators.handlers import get_handler_info
        info = get_handler_info(TestCommandHandler)
        assert info is not None
        assert info.handler_type == "command"
        assert info.message_types == [Command]

    def test_query_handler_decorator(self):
        """Test query handler decorator"""
        bus = QueryBusImpl()

        @query_handler(Query)
        class TestQueryHandler:
            async def handle(self, query):
                return "result"

        from lexigram.events.decorators.handlers import get_handler_info
        info = get_handler_info(TestQueryHandler)
        assert info is not None
        assert info.handler_type == "query"
        assert info.message_types == [Query]

    def test_event_handler_decorator(self):
        """Test event handler decorator"""
        bus = EventBusImpl()

        @event_handler(DomainEvent)
        class TestEventHandler:
            async def handle(self, event):
                pass

        from lexigram.events.decorators.handlers import get_handler_info
        info = get_handler_info(TestEventHandler)
        assert info is not None
        assert info.handler_type == "event"
        assert info.message_types == [DomainEvent]

    def test_event_handler_multiple_events(self):
        """Test event handler decorator with multiple events"""
        from lexigram.events.decorators.handlers import multi_event_handler
        bus = EventBusImpl()

        class OrderEvent(DomainEvent):
            order_id: str = "test"

        class PaymentEvent(DomainEvent):
            payment_id: str = "test"

        @multi_event_handler(OrderEvent, PaymentEvent)
        class TestEventHandler:
            async def handle(self, event):
                pass

        from lexigram.events.decorators.handlers import get_handler_info
        info = get_handler_info(TestEventHandler)
        assert info is not None
        assert info.handler_type == "event"
        assert OrderEvent in info.message_types
        assert PaymentEvent in info.message_types


class TestBaseBus:
    """Test base Bus functionality using concrete implementations"""

    def test_base_bus_creation(self):
        """Test base bus creation"""
        bus = CommandBusImpl()
        assert bus._middlewares == []
        assert bus._handlers == {}

    @pytest.mark.asyncio
    async def test_resolve_handler_manual_registration(self):
        """Test handler resolution from manual registrations"""
        bus = CommandBusImpl()
        handler = Mock()
        bus.register(Command, handler)

        resolved = await bus._resolve_handler(Command)
        assert resolved == handler

    @pytest.mark.asyncio
    async def test_resolve_handler_class_instantiation(self):
        """Test handler resolution with class instantiation"""
        bus = CommandBusImpl()

        class TestHandler:
            def __init__(self):
                self.value = "instantiated"

        bus.register(Command, TestHandler)
        resolved = await bus._resolve_handler(Command)

        assert isinstance(resolved, TestHandler)
        assert resolved.value == "instantiated"

    @pytest.mark.asyncio
    async def test_resolve_handler_class_instantiation_no_container(self):
        """Test handler resolution with class instantiation (no container)"""
        bus = CommandBusImpl()

        class TestHandler:
            def __init__(self):
                self.value = "instantiated"

        bus.register(Command, TestHandler)
        resolved = await bus._resolve_handler(Command)

        assert isinstance(resolved, TestHandler)
        assert resolved.value == "instantiated"

    @pytest.mark.asyncio
    async def test_resolve_handler_not_found(self):
        """Test handler resolution when not found"""
        bus = CommandBusImpl()

        with pytest.raises(HandlerNotFoundError):
            await bus._resolve_handler(Command)


    @pytest.mark.asyncio
    async def test_call_handler_function_handler(self):
        """Test calling a function handler"""
        bus = CommandBusImpl()

        async def handler_func(message):
            return "function_result"

        result = await bus._call_handler(handler_func, Command())
        assert result == "function_result"

    @pytest.mark.asyncio
    async def test_call_handler_sync_function_handler(self):
        """Test calling a synchronous function handler"""
        bus = CommandBusImpl()

        def handler_func(message):
            return "sync_result"

        result = await bus._call_handler(handler_func, Command())
        assert result == "sync_result"

    @pytest.mark.asyncio
    async def test_call_handler_object_with_handle(self):
        """Test calling an object with handle method"""
        bus = CommandBusImpl()

        class HandlerObject:
            async def handle(self, message):
                return "object_result"

        handler = HandlerObject()
        result = await bus._call_handler(handler, Command())
        assert result == "object_result"

    @pytest.mark.asyncio
    async def test_call_handler_object_with_sync_handle(self):
        """Test calling an object with synchronous handle method"""
        bus = CommandBusImpl()

        class HandlerObject:
            def handle(self, message):
                return "sync_object_result"

        handler = HandlerObject()
        result = await bus._call_handler(handler, Command())
        assert result == "sync_object_result"

    def test_call_handler_invalid_type(self):
        """Test calling an invalid handler type"""
        bus = CommandBusImpl()

        with pytest.raises(TypeError) as exc_info:
            # This should be synchronous since it's not a valid handler
            import asyncio

            asyncio.run(bus._call_handler("invalid_handler", Command()))

        assert "Invalid handler type" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_pipeline_no_middlewares(self):
        """Test pipeline execution without middlewares"""
        bus = CommandBusImpl()

        async def handler(message):
            return "direct_result"

        result = await bus._execute_pipeline(Command(), handler)
        assert result == "direct_result"


    @pytest.mark.asyncio
    async def test_execute_pipeline_middleware_chain(self):
        """Test middleware chain execution in pipeline"""
        bus = CommandBusImpl()

        execution_order = []

        async def middleware1(msg, next_handler):
            execution_order.append("middleware1_start")
            result = await next_handler(msg)
            execution_order.append("middleware1_end")
            return result

        async def middleware2(msg, next_handler):
            execution_order.append("middleware2_start")
            result = await next_handler(msg)
            execution_order.append("middleware2_end")
            return result

        bus._middlewares = [middleware1, middleware2]

        async def final_handler(msg):
            execution_order.append("final_handler")
            return "chain_result"

        result = await bus._execute_pipeline(Command(), final_handler)

        assert result == "chain_result"
        assert execution_order == [
            "middleware1_start",
            "middleware2_start",
            "final_handler",
            "middleware2_end",
            "middleware1_end",
        ]


class TestMiddleware:
    """Test middleware functionality"""

    @pytest.mark.asyncio
    async def test_middleware_execution_order(self):
        """Test middleware execution order"""
        bus = CommandBusImpl()

        execution_order = []

        async def middleware1(cmd, next_handler):
            execution_order.append("middleware1_start")
            result = await next_handler(cmd)
            execution_order.append("middleware1_end")
            return result

        async def middleware2(cmd, next_handler):
            execution_order.append("middleware2_start")
            result = await next_handler(cmd)
            execution_order.append("middleware2_end")
            return result

        bus.use(middleware1).use(middleware2)

        command = Command()
        handler = AsyncMock()
        handler.return_value = "result"
        bus.register(Command, handler)

        result = await bus.dispatch(command)

        assert execution_order == [
            "middleware1_start",
            "middleware2_start",
            "middleware2_end",
            "middleware1_end",
        ]
        assert result == "result"

    @pytest.mark.asyncio
    async def test_middleware_can_modify_result(self):
        """Test middleware can modify handler result"""
        bus = CommandBusImpl()

        async def result_modifier(cmd, next_handler):
            result = await next_handler(cmd)
            return f"modified_{result}"

        bus.use(result_modifier)

        command = Command()
        handler = AsyncMock()
        handler.return_value = "original"
        bus.register(Command, handler)

        result = await bus.dispatch(command)

        assert result == "modified_original"
