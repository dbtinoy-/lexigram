"""Tests for GraphQL controller auth context integration.

This module tests that the GraphQL controller properly integrates with
the context factory to pass raw_request and handle authentication.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from lexigram.graphql.controllers.graphql import GraphQLController


@pytest.mark.asyncio
async def test_controller_passes_raw_request_to_context_factory() -> None:
    """Test that controller passes raw_request to context factory.

    The controller should pass the raw HTTP request to the context factory
    so it can be used for optional authentication and is available in the
    execution context.
    """
    # Arrange: Create mock provider with context factory
    mock_provider = Mock()
    mock_context_factory = Mock()
    mock_context_factory.create_context = AsyncMock()
    mock_provider.context_factory = mock_context_factory

    # Create mock executor
    mock_executor = Mock()
    mock_executor.execute = AsyncMock()
    from lexigram.result import Ok

    # Mock a successful execution result
    mock_response = Mock()
    mock_response.data = {"test": "result"}
    mock_response.errors = None
    mock_executor.execute.return_value = Ok(mock_response)
    mock_provider.executor = Mock(return_value=mock_executor)

    # Create controller with the mock provider
    controller = GraphQLController(provider=mock_provider)

    # Create mock request
    mock_request = Mock()
    mock_request.json = AsyncMock(return_value={"query": "{ test }"})
    mock_request.state = Mock(user=None)
    mock_request.scope = {"extensions": {}}

    # Act: Execute the GraphQL query
    await controller.execute(mock_request)

    # Assert: context_factory.create_context was called with raw_request
    mock_context_factory.create_context.assert_called_once()
    call_kwargs = mock_context_factory.create_context.call_args.kwargs
    assert "raw_request" in call_kwargs
    assert call_kwargs["raw_request"] == mock_request


@pytest.mark.asyncio
async def test_controller_passes_user_from_request_state() -> None:
    """Test that controller extracts user from request state.

    When middleware has set request.state.user, the controller should
    extract it and pass it to the context factory.
    """
    # Arrange: Create mock provider
    mock_provider = Mock()
    mock_context_factory = Mock()
    mock_context_factory.create_context = AsyncMock()
    mock_provider.context_factory = mock_context_factory

    mock_executor = Mock()
    mock_executor.execute = AsyncMock()
    from lexigram.result import Ok

    mock_response = Mock()
    mock_response.data = {"test": "result"}
    mock_response.errors = None
    mock_executor.execute.return_value = Ok(mock_response)
    mock_provider.executor = Mock(return_value=mock_executor)

    controller = GraphQLController(provider=mock_provider)

    # Create mock request with user in state
    mock_user = {"id": "user_123", "email": "user@example.com"}
    mock_request = Mock()
    mock_request.json = AsyncMock(return_value={"query": "{ test }"})
    mock_request.state = Mock(user=mock_user)
    mock_request.scope = {"extensions": {}}

    # Act: Execute the GraphQL query
    await controller.execute(mock_request)

    # Assert: user was passed to context factory
    mock_context_factory.create_context.assert_called_once()
    call_kwargs = mock_context_factory.create_context.call_args.kwargs
    assert "user" in call_kwargs
    assert call_kwargs["user"] == mock_user


@pytest.mark.asyncio
async def test_controller_passes_user_from_scope_extensions() -> None:
    """Test that controller extracts user from scope extensions as fallback.

    When request.state.user is None but user exists in scope extensions,
    the controller should use that.
    """
    # Arrange: Create mock provider
    mock_provider = Mock()
    mock_context_factory = Mock()
    mock_context_factory.create_context = AsyncMock()
    mock_provider.context_factory = mock_context_factory

    mock_executor = Mock()
    mock_executor.execute = AsyncMock()
    from lexigram.result import Ok

    mock_response = Mock()
    mock_response.data = {"test": "result"}
    mock_response.errors = None
    mock_executor.execute.return_value = Ok(mock_response)
    mock_provider.executor = Mock(return_value=mock_executor)

    controller = GraphQLController(provider=mock_provider)

    # Create mock request with user in scope extensions
    mock_user = {"id": "scope_user_456", "email": "scope@example.com"}
    mock_request = Mock()
    mock_request.json = AsyncMock(return_value={"query": "{ test }"})
    mock_request.state = Mock(user=None)
    mock_request.scope = {"extensions": {"user": mock_user}}

    # Act: Execute the GraphQL query
    await controller.execute(mock_request)

    # Assert: user from scope extensions was passed to context factory
    mock_context_factory.create_context.assert_called_once()
    call_kwargs = mock_context_factory.create_context.call_args.kwargs
    assert "user" in call_kwargs
    assert call_kwargs["user"] == mock_user


@pytest.mark.asyncio
async def test_controller_passes_container_in_metadata() -> None:
    """Test that controller passes container in metadata for DI access.

    The context factory needs access to the DI container for optional
    service resolution. The controller should pass it via metadata.
    """
    # Arrange: Create mock provider
    mock_provider = Mock()
    mock_context_factory = Mock()
    mock_context_factory.create_context = AsyncMock()
    mock_provider.context_factory = mock_context_factory

    mock_executor = Mock()
    mock_executor.execute = AsyncMock()
    from lexigram.result import Ok

    mock_response = Mock()
    mock_response.data = {"test": "result"}
    mock_response.errors = None
    mock_executor.execute.return_value = Ok(mock_response)
    mock_provider.executor = Mock(return_value=mock_executor)

    # Create controller with container
    controller = GraphQLController(provider=mock_provider)
    mock_container = Mock()
    controller.container = mock_container

    # Create mock request
    mock_request = Mock()
    mock_request.json = AsyncMock(return_value={"query": "{ test }"})
    mock_request.state = Mock(user=None)
    mock_request.scope = {"extensions": {}}

    # Act: Execute the GraphQL query
    await controller.execute(mock_request)

    # Assert: container was passed in metadata
    mock_context_factory.create_context.assert_called_once()
    call_kwargs = mock_context_factory.create_context.call_args.kwargs
    assert "metadata" in call_kwargs
    assert call_kwargs["metadata"]["container"] == mock_container
