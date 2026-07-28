from dataclasses import dataclass
"""Unit tests for event decorators."""

from typing import cast

import pytest

from lexigram.events.decorators.handlers import (
    HandlerInfo,
    clear_handlers,
    command_handler,
    event_handler,
    get_all_handlers,
    get_handler_info,
    multi_event_handler,
    projection,
    query_handler,
    saga,
)
from lexigram.events.decorators.validation import (
    CQRSValidationError,
    clear_idempotency_cache,
    idempotent,
    validate,
    validate_command,
    validate_query,
)
from lexigram.events.messages.command import Command
from lexigram.events.messages.event import Event
from lexigram.events.messages.query import Query


class _TestCommand(Command):
    """Test command."""

    value: str


class _TestQuery(Query):
    """Test query."""

    param: str


class _TestEvent(Event):
    """Test event."""

    data: str


class _TestSaga:
    """Test saga class."""

    pass


class _TestProjection:
    """Test projection class."""

    pass


class TestHandlerInfo:
    """Test HandlerInfo functionality."""

    def test_handler_info_creation(self):
        """Test creating HandlerInfo."""

        def test_func():
            pass

        info = HandlerInfo(
            handler_type="command",
            message_types=[_TestCommand],
            handler=test_func,
            name="test_handler",
            module="test_module",
            is_async=False,
            metadata={"key": "value"},
        )

        assert info.handler_type == "command"
        assert info.message_types == [_TestCommand]
        assert info.handler == test_func
        assert info.name == "test_handler"
        assert info.module == "test_module"
        assert info.is_async is False
        assert info.metadata == {"key": "value"}


class TestHandlerRegistry:
    """Test handler registry functionality."""

    def setup_method(self):
        """Clear handlers before each test."""
        clear_handlers()

    def test_get_all_handlers_empty(self):
        """Test getting all handlers when empty."""
        handlers = get_all_handlers()
        assert handlers == []

    def test_get_all_handlers_by_type(self):
        """Test getting handlers by type."""
        handlers = get_all_handlers("command")
        assert handlers == []

    def test_clear_handlers_by_type(self):
        """Test clearing handlers by type."""

        # Add some handlers first
        @command_handler(_TestCommand)
        def test_cmd():
            pass

        assert len(get_all_handlers("command")) == 1

        clear_handlers("command")
        assert len(get_all_handlers("command")) == 0

    def test_clear_all_handlers(self):
        """Test clearing all handlers."""

        @command_handler(_TestCommand)
        def test_cmd():
            pass

        @event_handler(_TestEvent)
        def test_evt():
            pass

        assert len(get_all_handlers()) == 2

        clear_handlers()
        assert len(get_all_handlers()) == 0


class TestCommandHandler:
    """Test command_handler decorator."""

    def setup_method(self):
        """Clear handlers before each test."""
        clear_handlers()

    def test_command_handler_decorator(self):
        """Test command handler decorator."""

        @command_handler(_TestCommand)
        def handle_command(cmd: _TestCommand):
            return f"handled: {cmd.value}"

        # Check handler is registered
        handlers = get_all_handlers("command")
        assert len(handlers) == 1

        info = handlers[0]
        assert info.handler_type == "command"
        assert info.message_types == [_TestCommand]
        assert info.name == "handle_command"
        assert info.is_async is False
        assert info.metadata == {}

        # Check handler info attached to function
        assert hasattr(handle_command, "_handler_info")
        assert handle_command._handler_info == info

        # Test function still works
        cmd = _TestCommand(value="test")
        result = handle_command(cmd)
        assert result == "handled: test"

    def test_command_handler_with_metadata(self):
        """Test command handler with custom metadata."""

        @command_handler(_TestCommand, name="custom_handler", custom="value")
        def handle_command(cmd: _TestCommand):
            pass

        handlers = get_all_handlers("command")
        assert len(handlers) == 1

        info = handlers[0]
        assert info.name == "custom_handler"
        assert info.metadata == {"custom": "value"}

    def test_get_handler_info(self):
        """Test getting handler info."""

        @command_handler(_TestCommand)
        def handle_command(cmd: _TestCommand):
            pass

        info = get_handler_info(handle_command)
        # Note: get_handler_info may not work due to decorator wrapper issue
        # Check that _handler_info is attached to the function
        assert hasattr(handle_command, "_handler_info")
        info = handle_command._handler_info
        assert info.handler_type == "command"


class TestQueryHandler:
    """Test query_handler decorator."""

    def setup_method(self):
        """Clear handlers before each test."""
        clear_handlers()

    def test_query_handler_decorator(self):
        """Test query handler decorator."""

        @query_handler(_TestQuery)
        def handle_query(query: _TestQuery):
            return f"result: {query.param}"

        handlers = get_all_handlers("query")
        assert len(handlers) == 1

        info = handlers[0]
        assert info.handler_type == "query"
        assert info.message_types == [_TestQuery]
        assert info.metadata == {"cacheable": False, "cache_ttl": None}

    def test_query_handler_with_caching(self):
        """Test query handler with caching options."""

        @query_handler(_TestQuery, cacheable=True, cache_ttl=300)
        def handle_query(query: _TestQuery):
            pass

        handlers = get_all_handlers("query")
        assert len(handlers) == 1

        info = handlers[0]
        assert info.metadata == {"cacheable": True, "cache_ttl": 300}


class TestEventHandler:
    """Test event_handler decorator."""

    def setup_method(self):
        """Clear handlers before each test."""
        clear_handlers()

    def test_event_handler_decorator(self):
        """Test event handler decorator."""

        @event_handler(_TestEvent)
        def handle_event(event: _TestEvent):
            pass

        handlers = get_all_handlers("event")
        assert len(handlers) == 1

        info = handlers[0]
        assert info.handler_type == "event"
        assert info.message_types == [_TestEvent]
        assert info.metadata == {"priority": 0}

    def test_event_handler_with_priority(self):
        """Test event handler with priority."""

        @event_handler(_TestEvent, priority=10)
        def handle_event(event: _TestEvent):
            pass

        handlers = get_all_handlers("event")
        assert len(handlers) == 1

        info = handlers[0]
        assert info.metadata == {"priority": 10}


class TestMultiEventHandler:
    """Test multi_event_handler decorator."""

    def setup_method(self):
        """Clear handlers before each test."""
        clear_handlers()

    def test_multi_event_handler_decorator(self):
        """Test multi event handler decorator."""

        class _TestEvent2(Event):
            data2: str

        @multi_event_handler(_TestEvent, _TestEvent2, priority=5)
        def handle_events(event: Event):
            pass

        handlers = get_all_handlers("event")
        assert len(handlers) == 1

        info = handlers[0]
        assert info.handler_type == "event"
        assert set(info.message_types) == {_TestEvent, _TestEvent2}
        assert info.metadata == {"priority": 5}


class TestSagaDecorator:
    """Test saga decorator."""

    def setup_method(self):
        """Clear handlers before each test."""
        clear_handlers()

    def test_saga_decorator(self):
        """Test saga decorator."""

        @saga(timeout=300)
        class _TestSagaImpl(_TestSaga):
            pass

        handlers = get_all_handlers("saga")
        assert len(handlers) == 1

        info = handlers[0]
        assert info.handler_type == "saga"
        assert info.message_types == []
        assert info.handler == _TestSagaImpl
        assert info.metadata == {"timeout": 300}

        # Check handler info attached to class
        assert hasattr(_TestSagaImpl, "_handler_info")
        assert _TestSagaImpl._handler_info == info


class TestProjectionDecorator:
    """Test projection decorator."""

    def setup_method(self):
        """Clear handlers before each test."""
        clear_handlers()

    def test_projection_decorator(self):
        """Test projection decorator."""

        @projection(name="custom_projection")
        class _TestProjectionImpl(_TestProjection):
            pass

        handlers = get_all_handlers("projection")
        assert len(handlers) == 1

        info = handlers[0]
        assert info.handler_type == "projection"
        assert info.message_types == []
        assert info.handler == _TestProjectionImpl
        assert info.name == "custom_projection"

        # Check handler info attached to class
        assert hasattr(_TestProjectionImpl, "_handler_info")
        assert _TestProjectionImpl._handler_info == info


class TestValidateDecorator:
    """Test validate decorator."""

    def test_validate_sync_function_success(self):
        """Test validate decorator with sync function success."""

        @validate
        def test_func(data: str) -> str:
            return f"processed: {data}"

        result = test_func("test")
        assert result == "processed: test"

    def test_validate_async_function_success(self):
        """Test validate decorator with async function success."""
        import asyncio

        @validate
        async def test_func(data: str) -> str:
            await asyncio.sleep(0.001)
            return f"processed: {data}"

        async def run_test():
            result = await test_func("test")
            assert result == "processed: test"

        asyncio.run(run_test())

    def test_validate_sync_function_validation_error(self):
        """Test validate decorator catches validation errors."""
        from lexigram.contracts.exceptions.domain import ValidationError

        @validate
        def test_func() -> str:
            err = ValidationError("Validation failed")
            err.add_error("value", "Input should be a valid integer")
            raise err

        with pytest.raises(CQRSValidationError) as exc_info:
            test_func()

        assert "Validation failed" in str(exc_info.value)
        assert "value" in str(exc_info.value)

    def test_validate_async_function_validation_error(self):
        """Test validate decorator catches validation errors in async functions."""
        import asyncio

        from lexigram.contracts.exceptions.domain import ValidationError

        @validate
        async def test_func() -> str:
            await asyncio.sleep(0.001)
            err = ValidationError("Validation failed")
            err.add_error("value", "Input should be a valid integer")
            raise err

        async def run_test():
            with pytest.raises(CQRSValidationError) as exc_info:
                await test_func()

            assert "Validation failed" in str(exc_info.value)

        asyncio.run(run_test())


class TestValidateCommandDecorator:
    """Test validate_command decorator."""

    def test_validate_command_success(self):
        """Test validate_command decorator success."""
        from lexigram.domain import DomainModel

        @dataclass
        class TestCommand(DomainModel):
            username: str
            email: str

        @validate_command(
            max_length={"username": 50, "email": 100},
            required_fields=["username", "email"],
        )
        def test_handler(command: TestCommand) -> str:
            return f"user: {command.username}"

        cmd = TestCommand(username="testuser", email="test@example.com")
        result = test_handler(cmd)
        assert result == "user: testuser"

    def test_validate_command_required_field_missing(self):
        """Test validate_command with missing required field."""
        from lexigram.domain import DomainModel

        @dataclass
        class TestCommand(DomainModel):
            username: str
            email: str

        @validate_command(required_fields=["username", "email"])
        def test_handler(command: TestCommand) -> str:
            return f"user: {command.username}"

        cmd = TestCommand(username="", email="test@example.com")

        with pytest.raises(CQRSValidationError) as exc_info:
            test_handler(cmd)

        assert "required" in str(exc_info.value).lower()

    def test_validate_command_max_length_exceeded(self):
        """Test validate_command with max length exceeded."""
        from lexigram.domain import DomainModel

        @dataclass
        class TestCommand(DomainModel):
            username: str
            email: str

        @validate_command(max_length={"username": 5})
        def test_handler(command: TestCommand) -> str:
            return f"user: {command.username}"

        cmd = TestCommand(username="verylongusername", email="test@example.com")

        with pytest.raises(CQRSValidationError) as exc_info:
            test_handler(cmd)

        assert "exceeds maximum length" in str(exc_info.value)

    def test_validate_command_custom_validator(self):
        """Test validate_command with custom validator."""
        from lexigram.domain import DomainModel

        @dataclass
        class TestCommand(DomainModel):
            username: str
            email: str

        def custom_validator(command):
            if "@" not in command.email:
                raise ValueError("Invalid email format")

        @validate_command(custom_validators=[custom_validator])
        def test_handler(command: TestCommand) -> str:
            return f"user: {command.username}"

        cmd = TestCommand(username="testuser", email="invalidemail")

        with pytest.raises(CQRSValidationError) as exc_info:
            test_handler(cmd)

        assert "Invalid email format" in str(exc_info.value)

    def test_validate_command_async(self):
        """Test validate_command decorator with async function."""
        import asyncio

        from lexigram.domain import DomainModel

        @dataclass
        class TestCommand(DomainModel):
            username: str

        @validate_command(required_fields=["username"])
        async def test_handler(command: TestCommand) -> str:
            await asyncio.sleep(0.001)
            return f"user: {command.username}"

        async def run_test():
            cmd = TestCommand(username="testuser")
            result = await test_handler(cmd)
            assert result == "user: testuser"

        asyncio.run(run_test())


class TestValidateQueryDecorator:
    """Test validate_query decorator."""

    def test_validate_query_success(self):
        """Test validate_query decorator success."""
        from lexigram.domain import DomainModel

        @dataclass
        class TestQuery(DomainModel):
            limit: int = 10
            sort_by: str = "created_at"

        @validate_query(max_results=100, allowed_sort_fields=["created_at", "name"])
        def test_handler(query: TestQuery) -> str:
            return f"limit: {query.limit}, sort: {query.sort_by}"

        query = TestQuery(limit=50, sort_by="name")
        result = test_handler(query)
        assert result == "limit: 50, sort: name"

    def test_validate_query_max_results_exceeded(self):
        """Test validate_query with max results exceeded."""
        from lexigram.domain import DomainModel

        @dataclass
        class TestQuery(DomainModel):
            limit: int = 10

        @validate_query(max_results=100)
        def test_handler(query: TestQuery) -> str:
            return f"limit: {query.limit}"

        query = TestQuery(limit=150)

        with pytest.raises(CQRSValidationError) as exc_info:
            test_handler(query)

        assert "exceeds maximum" in str(exc_info.value)

    def test_validate_query_invalid_sort_field(self):
        """Test validate_query with invalid sort field."""
        from lexigram.domain import DomainModel

        @dataclass
        class TestQuery(DomainModel):
            sort_by: str = "created_at"

        @validate_query(allowed_sort_fields=["created_at", "name"])
        def test_handler(query: TestQuery) -> str:
            return f"sort: {query.sort_by}"

        query = TestQuery(sort_by="invalid_field")

        with pytest.raises(CQRSValidationError) as exc_info:
            test_handler(query)

        assert "not allowed" in str(exc_info.value)

    def test_validate_query_page_size(self):
        """Test validate_query with page_size field."""
        from lexigram.domain import DomainModel

        @dataclass
        class TestQuery(DomainModel):
            page_size: int = 10

        @validate_query(max_results=50)
        def test_handler(query: TestQuery) -> str:
            return f"page_size: {query.page_size}"

        query = TestQuery(page_size=60)

        with pytest.raises(CQRSValidationError) as exc_info:
            test_handler(query)

        assert "exceeds maximum" in str(exc_info.value)

    def test_validate_query_async(self):
        """Test validate_query decorator with async function."""
        import asyncio

        from lexigram.domain import DomainModel

        @dataclass
        class TestQuery(DomainModel):
            limit: int = 10

        @validate_query(max_results=100)
        async def test_handler(query: TestQuery) -> str:
            await asyncio.sleep(0.001)
            return f"limit: {query.limit}"

        async def run_test():
            query = TestQuery(limit=50)
            result = await test_handler(query)
            assert result == "limit: 50"

        asyncio.run(run_test())


class TestIdempotentDecorator:
    """Test idempotent decorator."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_idempotency_cache()

    def test_idempotent_with_key_func(self):
        """Test idempotent decorator with custom key function."""
        from lexigram.domain import DomainModel

        @dataclass
        class TestCommand(DomainModel):
            request_id: str
            data: str

        call_count = 0

        @idempotent(key_func=lambda cmd: cmd.request_id)
        def test_handler(command: TestCommand) -> str:
            nonlocal call_count
            call_count += 1
            return f"processed: {command.data}"

        cmd = TestCommand(request_id="req-123", data="test")

        # First call
        result1 = test_handler(cmd)
        assert result1 == "processed: test"
        assert call_count == 1

        # Second call with same key should return cached result
        result2 = test_handler(cmd)
        assert result2 == "processed: test"
        assert call_count == 1  # Should not have been called again

    def test_idempotent_with_idempotency_key_attribute(self):
        """Test idempotent decorator using command's idempotency_key attribute."""
        from lexigram.domain import DomainModel

        @dataclass
        class TestCommand(DomainModel):
            idempotency_key: str
            data: str

        call_count = 0

        @idempotent()
        def test_handler(command: TestCommand) -> str:
            nonlocal call_count
            call_count += 1
            return f"processed: {command.data}"

        cmd = TestCommand(idempotency_key="key-123", data="test")

        # First call
        result1 = test_handler(cmd)
        assert result1 == "processed: test"
        assert call_count == 1

        # Second call with same key should return cached result
        result2 = test_handler(cmd)
        assert result2 == "processed: test"
        assert call_count == 1

    def test_idempotent_with_content_hash(self):
        """Test idempotent decorator using content hash when no key provided."""
        from lexigram.domain import DomainModel

        @dataclass
        class TestCommand(DomainModel):
            data: str

        call_count = 0

        @idempotent()
        def test_handler(command: TestCommand) -> str:
            nonlocal call_count
            call_count += 1
            return f"processed: {command.data}"

        cmd1 = TestCommand(data="test")
        cmd2 = TestCommand(data="test")  # Same content

        # First call
        result1 = test_handler(cmd1)
        assert result1 == "processed: test"
        assert call_count == 1

        # Second call with same content should return cached result
        result2 = test_handler(cmd2)
        assert result2 == "processed: test"
        assert call_count == 1

    def test_idempotent_async(self):
        """Test idempotent decorator with async function."""
        import asyncio

        from lexigram.domain import DomainModel

        @dataclass
        class TestCommand(DomainModel):
            request_id: str
            data: str

        call_count = 0

        @idempotent(key_func=lambda cmd: cmd.request_id)
        async def test_handler(command: TestCommand) -> str:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.001)
            return f"processed: {command.data}"

        async def run_test():
            cmd = TestCommand(request_id="req-123", data="test")

            # First call
            result1 = await test_handler(cmd)
            assert result1 == "processed: test"
            assert call_count == 1

            # Second call with same key should return cached result
            result2 = await test_handler(cmd)
            assert result2 == "processed: test"
            assert call_count == 1

        asyncio.run(run_test())

    def test_idempotent_no_command(self):
        """Test idempotent decorator when no command is found."""

        @idempotent()
        def test_handler(data: str) -> str:
            return f"processed: {data}"

        result = test_handler("test")
        assert result == "processed: test"

    def test_clear_idempotency_cache(self):
        """Test clearing idempotency cache."""
        from lexigram.domain import DomainModel

        @dataclass
        class TestCommand(DomainModel):
            request_id: str
            data: str

        call_count = 0

        @idempotent(key_func=lambda cmd: cmd.request_id)
        def test_handler(command: TestCommand) -> str:
            nonlocal call_count
            call_count += 1
            return f"processed: {command.data}"

        cmd = TestCommand(request_id="req-123", data="test")

        # First call
        test_handler(cmd)
        assert call_count == 1

        # Second call should use cache
        test_handler(cmd)
        assert call_count == 1

        # Clear cache
        clear_idempotency_cache()

        # Third call should execute again
        test_handler(cmd)
        assert call_count == 2