"""Unit tests for GraphQL execution."""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import strawberry
from datetime import datetime, UTC
from strawberry.types import ExecutionResult

from lexigram.graphql.core.execution import (
    GraphQLExecutorProtocol,
    ExecutionContextProtocol,
    execute_query,
    GraphQLContext,
    GraphQLTimeoutError,
    ExecutionError
)

@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "world"

    @strawberry.field
    async def async_hello(self) -> str:
        return "async world"

    @strawberry.field
    def error(self) -> str:
        raise ValueError("Intentional error")

schema = strawberry.Schema(query=Query)

class TestGraphQLExecutor:
    """Test GraphQLExecutorProtocol functionality."""

    @pytest.fixture
    def executor(self):
        """Create executor instance."""
        return GraphQLExecutorProtocol(schema)

    @pytest.fixture
    def context(self):
        """Create GraphQL context."""
        return GraphQLContext(request=MagicMock())

    @pytest.mark.asyncio
    async def test_execute_simple_query(self, executor):
        """Test executing a simple query."""
        query = "{ hello }"
        result_obj = await executor.execute(query)

        assert result_obj.is_ok()
        result = result_obj.unwrap()
        assert result.data == {"hello": "world"}
        assert not result.errors

    @pytest.mark.asyncio
    async def test_execute_async_query(self, executor):
        """Test executing an async query."""
        query = "{ asyncHello }"
        result_obj = await executor.execute(query)

        assert result_obj.is_ok()
        result = result_obj.unwrap()
        assert result.data == {"asyncHello": "async world"}
        assert not result.errors

    @pytest.mark.asyncio
    async def test_execute_with_error(self, executor):
        """Test executing a query that raises an error."""
        query = "{ error }"
        result_obj = await executor.execute(query)

        assert result_obj.is_ok()
        result = result_obj.unwrap()
        assert result.data is None  # Or partial data depending on error handling strategy
        assert result.errors
        assert result.errors[0].message == "Intentional error"

    @pytest.mark.asyncio
    async def test_execute_publishes_lifecycle_events(self):
        """Test that execution publishes BeforeExecuteEvent and AfterExecuteEvent via EventBusProtocol."""
        from lexigram.graphql.events import AfterExecuteEvent, BeforeExecuteEvent

        mock_bus = AsyncMock()
        executor = GraphQLExecutorProtocol(schema, event_bus=mock_bus)

        await executor.execute("{ hello }")

        assert mock_bus.publish.call_count == 2
        published_types = [type(call.args[0]) for call in mock_bus.publish.call_args_list]
        assert BeforeExecuteEvent in published_types
        assert AfterExecuteEvent in published_types

    @pytest.mark.asyncio
    async def test_execution_context_metrics(self, context):
        """Test ExecutionContextProtocol metrics."""
        exec_context = ExecutionContextProtocol(context=context)
        
        # Simulate time passing
        start_time = datetime.now(UTC)
        exec_context.start_time = start_time
        
        exec_context.mark_complete()
        
        assert exec_context.end_time is not None
        assert exec_context.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_execute_timeout(self, executor):
        """Test execution timeout returns Err(GraphQLTimeoutError)."""
        async def slow_execute(*args, **kwargs):
            await asyncio.sleep(0.1)
            return ExecutionResult(data={"hello": "world"}, errors=[])

        with patch.object(executor, '_execute_internal', side_effect=slow_execute):
            result_obj = await executor.execute("{ hello }", timeout_secs=0.01)

        assert result_obj.is_err()
        assert isinstance(result_obj.unwrap_err(), GraphQLTimeoutError)

class TestExecuteQuery:
    """Test execute_query convenience function."""

    @pytest.mark.asyncio
    async def test_execute_query_helper(self):
        """Test helper function."""
        result = await execute_query(schema, "{ hello }")
        assert result.data == {"hello": "world"}
