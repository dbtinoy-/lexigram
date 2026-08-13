"""Tests for GraphQL context factory auth and principal resolution.

This module tests the optional authentication and principal resolution
capabilities of the ContextFactory, ensuring it can:
1. Use middleware-provided user when present
2. Optionally authenticate from raw_request when user is missing
3. Resolve a principal via GraphQLPrincipalResolverProtocol
4. Attach the resolved principal to the returned context
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from lexigram.contracts.auth import AuthenticatorProtocol
from lexigram.contracts.graphql import (
    GraphQLPrincipal,
    GraphQLPrincipalResolverProtocol,
)
from lexigram.graphql.core.context import ContextFactory, GraphQLRequest


class FakeAuthenticator:
    """Fake authenticator for testing optional auth lookup."""

    async def authenticate(self, request: Any) -> Any:
        """Return a mock authenticated user."""
        return {"id": "auth_user_123", "email": "auth@example.com"}


class FakePrincipalResolver:
    """Fake principal resolver for testing."""

    async def resolve_principal(
        self, user: Any, request: Any = None
    ) -> GraphQLPrincipal:
        """Resolve a GraphQLPrincipal from user data."""
        if isinstance(user, dict):
            return GraphQLPrincipal(
                internal_user_id=user.get("id"),
                subject_id=user.get("sub"),
                email=user.get("email"),
                raw_user=user,
            )
        return GraphQLPrincipal(raw_user=user)


@pytest.mark.asyncio
async def test_context_factory_optionally_authenticates_and_resolves_principal() -> None:
    """Test that ContextFactory can optionally authenticate and resolve principal.

    When no user is provided but a raw_request is available, and the DI
    resolver can provide an AuthenticatorProtocol, the factory should:
    1. Resolve AuthenticatorProtocol from the DI container
    2. Call authenticate(raw_request) to get a user
    3. Resolve GraphQLPrincipalResolverProtocol
    4. Call resolve_principal(user, request)
    5. Attach the principal to the context
    """
    # Arrange: Create mock resolver that can provide auth and principal resolver
    mock_resolver = Mock()
    mock_resolver.resolve_optional = AsyncMock()

    # Setup the resolver to return our fakes
    async def resolve_optional_side_effect(protocol: type) -> Any:
        if protocol == AuthenticatorProtocol:
            return FakeAuthenticator()
        if protocol == GraphQLPrincipalResolverProtocol:
            return FakePrincipalResolver()
        return None

    mock_resolver.resolve_optional.side_effect = resolve_optional_side_effect

    # Create a mock raw_request
    mock_request = Mock()

    # Create factory with the mock resolver
    factory = ContextFactory(resolver=mock_resolver)

    # Act: Create context without user but with raw_request
    context = await factory.create_context(
        request=GraphQLRequest(query="{ test }"),
        user=None,
        raw_request=mock_request,
    )

    # Assert: Principal should be resolved and attached
    assert context.principal is not None
    assert context.principal.internal_user_id == "auth_user_123"
    assert context.principal.email == "auth@example.com"
    assert context.principal.raw_user == {
        "id": "auth_user_123",
        "email": "auth@example.com",
    }


@pytest.mark.asyncio
async def test_context_factory_keeps_principal_none_when_no_user_exists() -> None:
    """Test that principal stays None when no user can be resolved.

    When no user is provided, no raw_request is available, or authentication
    fails, the context should have principal=None to support anonymous access.
    """
    # Arrange: Factory with no resolver (can't do optional auth)
    factory = ContextFactory(resolver=None)

    # Act: Create context without user and without raw_request
    context = await factory.create_context(
        request=GraphQLRequest(query="{ test }"),
        user=None,
        raw_request=None,
    )

    # Assert: Principal should be None
    assert context.principal is None


@pytest.mark.asyncio
async def test_context_factory_uses_middleware_user_when_provided() -> None:
    """Test that factory uses user from middleware when provided.

    When the middleware has already authenticated and provided a user,
    the factory should use it directly and resolve a principal without
    attempting optional authentication.
    """
    # Arrange: Create mock resolver with principal resolver
    mock_resolver = Mock()
    mock_resolver.resolve_optional = AsyncMock()

    async def resolve_optional_side_effect(protocol: type) -> Any:
        if protocol == GraphQLPrincipalResolverProtocol:
            return FakePrincipalResolver()
        return None

    mock_resolver.resolve_optional.side_effect = resolve_optional_side_effect

    factory = ContextFactory(resolver=mock_resolver)

    # Act: Create context with middleware-provided user
    middleware_user = {"id": "middleware_user_456", "email": "middleware@example.com"}
    context = await factory.create_context(
        request=GraphQLRequest(query="{ test }"),
        user=middleware_user,
        raw_request=Mock(),
    )

    # Assert: Principal should be resolved from middleware user
    assert context.principal is not None
    assert context.principal.internal_user_id == "middleware_user_456"
    assert context.principal.email == "middleware@example.com"
    assert context.principal.raw_user == middleware_user

    # Assert: AuthenticatorProtocol was never resolved (user was provided)
    # We can check this by verifying resolve_optional was only called once
    # (for principal resolver, not for authenticator)
    calls = mock_resolver.resolve_optional.call_args_list
    protocols_resolved = [call[0][0] for call in calls]
    assert AuthenticatorProtocol not in protocols_resolved


@pytest.mark.asyncio
async def test_context_factory_fallback_principal_when_no_resolver() -> None:
    """Test fallback principal creation when no resolver is registered.

    When a user exists but no GraphQLPrincipalResolverProtocol is registered,
    the factory should create a fallback principal with raw_user set.
    """
    # Arrange: Factory with resolver that can't provide principal resolver
    mock_resolver = Mock()
    mock_resolver.resolve_optional = AsyncMock(return_value=None)

    factory = ContextFactory(resolver=mock_resolver)

    # Act: Create context with user but no principal resolver available
    user = {"id": "fallback_user_789", "email": "fallback@example.com"}
    context = await factory.create_context(
        request=GraphQLRequest(query="{ test }"),
        user=user,
        raw_request=None,
    )

    # Assert: Principal should exist with raw_user fallback
    assert context.principal is not None
    assert context.principal.raw_user == user
    # Other fields should be None (not extracted by fallback)
    assert context.principal.internal_user_id is None
    assert context.principal.subject_id is None
    assert context.principal.email is None
