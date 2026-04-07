"""Tests for GraphQL events and execution types."""

import pytest

from lexigram.graphql.events import (
    AfterExecuteEvent,
    BeforeExecuteEvent,
    OnErrorEvent,
)


class TestBeforeExecuteEvent:
    """Tests for BeforeExecuteEvent."""

    def test_before_execute_event_creation(self) -> None:
        """Test creating BeforeExecuteEvent."""
        from lexigram.graphql.core.execution import ExecutionContextProtocol

        from lexigram.graphql.core.context import GraphQLContext, GraphQLRequest

        ctx = ExecutionContextProtocol(
            context=GraphQLContext(
                request=GraphQLRequest(
                    query="query { users { id } }",
                    operation_name=None,
                    variables={},
                )
            )
        )
        event = BeforeExecuteEvent(execution_context=ctx)
        assert event.execution_context is ctx


class TestAfterExecuteEvent:
    """Tests for AfterExecuteEvent."""

    def test_after_execute_event_creation(self) -> None:
        """Test creating AfterExecuteEvent."""
        from lexigram.graphql.core.execution import ExecutionContextProtocol

        from lexigram.graphql.core.context import GraphQLContext, GraphQLRequest

        ctx = ExecutionContextProtocol(
            context=GraphQLContext(
                request=GraphQLRequest(
                    query="query { users { id } }",
                    operation_name=None,
                    variables={},
                )
            )
        )
        result = {"data": {"users": []}}
        event = AfterExecuteEvent(execution_context=ctx, result=result)
        assert event.execution_context is ctx
        assert event.result == result


class TestOnErrorEvent:
    """Tests for OnErrorEvent."""

    def test_on_error_event_creation(self) -> None:
        """Test creating OnErrorEvent."""
        from lexigram.graphql.core.execution import ExecutionContextProtocol

        from lexigram.graphql.core.context import GraphQLContext, GraphQLRequest

        ctx = ExecutionContextProtocol(
            context=GraphQLContext(
                request=GraphQLRequest(
                    query="query { users { id } }",
                    operation_name=None,
                    variables={},
                )
            )
        )
        error = ValueError("Something went wrong")
        event = OnErrorEvent(execution_context=ctx, error=error)
        assert event.execution_context is ctx
        assert event.error is error
