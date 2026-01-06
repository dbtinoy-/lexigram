"""Pytest fixtures for lexigram-auth testing.

This module provides comprehensive pytest fixtures for testing lexigram-auth
functionality, integrating with the lexigram.testing infrastructure.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from lexigram.logging import get_logger

logger = get_logger(__name__)

pytest_asyncio: Any | None = None
try:
    import pytest_asyncio as _pytest_asyncio

    pytest_asyncio = _pytest_asyncio
except ImportError as e:
    logger.warning("pytest_asyncio not available: %s", e)
    pytest_asyncio = None

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable

    from lexigram.testing.clients.auth.bed import AuthTestBed
    from lexigram.testing.clients.auth.client import AuthTestClient
    from lexigram.testing.clients.auth.types import AuthTestToken, AuthTestUser


# Runtime import of client helpers (placed before optional pytest-asyncio import to
# follow import ordering rules and avoid E402)
from lexigram.testing.clients.auth.bed import AuthTestBed
from lexigram.testing.clients.auth.client import AuthTestClient
from lexigram.testing.clients.auth.types import (
    AuthTestToken,
    AuthTestUser,
)

# Choose the async fixture decorator depending on pytest-asyncio availability
async_fixture: Callable[..., Any] = (
    pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture
)


# Test bed fixtures
@async_fixture
async def auth_test_bed() -> AsyncGenerator[AuthTestBed, None]:
    """Provide an auth test bed for testing.

    Yields:
        AuthTestBed: Configured test bed with auth providers
    """
    async with AuthTestBed() as bed:
        yield bed


@pytest.fixture
def auth_test_client(auth_test_bed: AuthTestBed) -> AuthTestClient:
    """Provide an auth test client.

    Args:
        auth_test_bed: The auth test bed

    Returns:
        AuthTestClient: Configured test client
    """
    return AuthTestClient(auth_test_bed)


# User fixtures
@pytest.fixture
def test_user_admin() -> Any:
    """Provide a test admin user."""
    return AuthTestUser.create(
        username="admin",
        email="admin@example.com",
        password="admin123",
        roles=["admin", "user"],
        permissions=["read", "write", "delete", "admin"],
    )


@pytest.fixture
def test_user_regular() -> Any:
    """Provide a regular test user."""
    return AuthTestUser.create(
        username="user",
        email="user@example.com",
        password="user123",
        roles=["user"],
        permissions=["read", "write"],
    )


@pytest.fixture
def test_user_moderator() -> Any:
    """Provide a test moderator user."""
    return AuthTestUser.create(
        username="moderator",
        email="moderator@example.com",
        password="mod123",
        roles=["moderator", "user"],
        permissions=["read", "write", "moderate"],
    )


@pytest.fixture
def test_user_inactive() -> Any:
    """Provide an inactive test user."""
    return AuthTestUser.create(
        username="inactive",
        email="inactive@example.com",
        password="inactive123",
        roles=["user"],
        permissions=["read"],
        is_active=False,
    )


@pytest.fixture
def test_user_unverified() -> Any:
    """Provide an unverified test user."""
    return AuthTestUser.create(
        username="unverified",
        email="unverified@example.com",
        password="unverified123",
        roles=["user"],
        permissions=["read"],
        is_verified=False,
    )


@async_fixture
async def created_test_user_admin(
    auth_test_client: AuthTestClient,
    test_user_admin: AuthTestUser,
) -> AuthTestUser:
    """Provide a created admin test user in the system.

    Args:
        auth_test_client: The auth test client
        test_user_admin: The admin test user template

    Returns:
        AuthTestUser: Created admin user
    """
    return await auth_test_client.create_test_user(
        username=test_user_admin.username,
        email=test_user_admin.email,
        password=test_user_admin.password,
        roles=test_user_admin.roles,
        permissions=test_user_admin.permissions,
    )


@async_fixture
async def created_test_user_regular(
    auth_test_client: AuthTestClient,
    test_user_regular: AuthTestUser,
) -> AuthTestUser:
    """Provide a created regular test user in the system.

    Args:
        auth_test_client: The auth test client
        test_user_regular: The regular test user template

    Returns:
        AuthTestUser: Created regular user
    """
    return await auth_test_client.create_test_user(
        username=test_user_regular.username,
        email=test_user_regular.email,
        password=test_user_regular.password,
        roles=test_user_regular.roles,
        permissions=test_user_regular.permissions,
    )


@async_fixture
async def created_test_user_moderator(
    auth_test_client: AuthTestClient,
    test_user_moderator: AuthTestUser,
) -> AuthTestUser:
    """Provide a created moderator test user in the system.

    Args:
        auth_test_client: The auth test client
        test_user_moderator: The moderator test user template

    Returns:
        AuthTestUser: Created moderator user
    """
    return await auth_test_client.create_test_user(
        username=test_user_moderator.username,
        email=test_user_moderator.email,
        password=test_user_moderator.password,
        roles=test_user_moderator.roles,
        permissions=test_user_moderator.permissions,
    )


@async_fixture
async def created_test_user_inactive(
    auth_test_client: AuthTestClient,
    test_user_inactive: AuthTestUser,
) -> AuthTestUser:
    """Provide a created inactive test user in the system.

    Args:
        auth_test_client: The auth test client
        test_user_inactive: The inactive test user template

    Returns:
        AuthTestUser: Created inactive user
    """
    return await auth_test_client.create_test_user(
        username=test_user_inactive.username,
        email=test_user_inactive.email,
        password=test_user_inactive.password,
        roles=test_user_inactive.roles,
        permissions=test_user_inactive.permissions,
        is_active=test_user_inactive.is_active,
    )


@async_fixture
async def created_test_user_unverified(
    auth_test_client: AuthTestClient,
    test_user_unverified: AuthTestUser,
) -> AuthTestUser:
    """Provide a created unverified test user in the system.

    Args:
        auth_test_client: The auth test client
        test_user_unverified: The unverified test user template

    Returns:
        AuthTestUser: Created unverified user
    """
    return await auth_test_client.create_test_user(
        username=test_user_unverified.username,
        email=test_user_unverified.email,
        password=test_user_unverified.password,
        roles=test_user_unverified.roles,
        permissions=test_user_unverified.permissions,
        is_verified=test_user_unverified.is_verified,
    )


# Token fixtures
@async_fixture
async def admin_token(
    auth_test_client: AuthTestClient,
    created_test_user_admin: AuthTestUser,
) -> AuthTestToken:
    """Provide an authentication token for the admin user.

    Args:
        auth_test_client: The auth test client
        created_test_user_admin: The created admin user

    Returns:
        AuthTestToken: Admin authentication token
    """
    token = await auth_test_client.login_user(
        created_test_user_admin.username,
        created_test_user_admin.password,
    )
    assert token is not None
    return token


@async_fixture
async def user_token(
    auth_test_client: AuthTestClient,
    created_test_user_regular: AuthTestUser,
) -> AuthTestToken:
    """Provide an authentication token for the regular user.

    Args:
        auth_test_client: The auth test client
        created_test_user_regular: The created regular user

    Returns:
        AuthTestToken: Regular user authentication token
    """
    token = await auth_test_client.login_user(
        created_test_user_regular.username,
        created_test_user_regular.password,
    )
    assert token is not None
    return token


@async_fixture
async def moderator_token(
    auth_test_client: AuthTestClient,
    created_test_user_moderator: AuthTestUser,
) -> AuthTestToken:
    """Provide an authentication token for the moderator user.

    Args:
        auth_test_client: The auth test client
        created_test_user_moderator: The created moderator user

    Returns:
        AuthTestToken: Moderator authentication token
    """
    token = await auth_test_client.login_user(
        created_test_user_moderator.username,
        created_test_user_moderator.password,
    )
    assert token is not None
    return token


# Authorized request fixtures
@async_fixture
async def admin_request_context(
    auth_test_client: AuthTestClient,
    created_test_user_admin: AuthTestUser,
) -> dict:
    """Provide an authorized request context for admin user.

    Args:
        auth_test_client: The auth test client
        created_test_user_admin: The created admin user

    Returns:
        Dict: Request context with admin authorization
    """
    return await auth_test_client.create_authorized_request(created_test_user_admin)


@async_fixture
async def user_request_context(
    auth_test_client: AuthTestClient,
    created_test_user_regular: AuthTestUser,
) -> dict:
    """Provide an authorized request context for regular user.

    Args:
        auth_test_client: The auth test client
        created_test_user_regular: The created regular user

    Returns:
        Dict: Request context with user authorization
    """
    return await auth_test_client.create_authorized_request(created_test_user_regular)


@async_fixture
async def moderator_request_context(
    auth_test_client: AuthTestClient,
    created_test_user_moderator: AuthTestUser,
) -> dict:
    """Provide an authorized request context for moderator user.

    Args:
        auth_test_client: The auth test client
        created_test_user_moderator: The created moderator user

    Returns:
        Dict: Request context with moderator authorization
    """
    return await auth_test_client.create_authorized_request(created_test_user_moderator)


# Bulk user fixtures
@async_fixture
async def multiple_test_users(auth_test_client: AuthTestClient) -> list[AuthTestUser]:
    """Provide multiple test users for testing.

    Args:
        auth_test_client: The auth test client

    Returns:
        list[AuthTestUser]: List of created test users
    """
    users = []
    user_data = [
        ("alice", "alice@example.com", "alice123", ["user"], ["read", "write"]),
        ("bob", "bob@example.com", "bob123", ["user"], ["read"]),
        (
            "charlie",
            "charlie@example.com",
            "charlie123",
            ["moderator", "user"],
            ["read", "write", "moderate"],
        ),
        (
            "diana",
            "diana@example.com",
            "diana123",
            ["admin", "user"],
            ["read", "write", "delete", "admin"],
        ),
    ]

    for username, email, password, roles, permissions in user_data:
        user = await auth_test_client.create_test_user(
            username=username,
            email=email,
            password=password,
            roles=roles,
            permissions=permissions,
        )
        users.append(user)

    return users


@async_fixture
async def multiple_user_tokens(
    auth_test_client: AuthTestClient,
    multiple_test_users: list[AuthTestUser],
) -> list[AuthTestToken]:
    """Provide authentication tokens for multiple users.

    Args:
        auth_test_client: The auth test client
        multiple_test_users: The multiple test users

    Returns:
        list[AuthTestToken]: List of authentication tokens
    """
    tokens: list[AuthTestToken] = []
    for user in multiple_test_users:
        token = await auth_test_client.login_user(user.name, user.password)  # type: ignore[attr-defined]
        assert token is not None
        tokens.append(token)

    return tokens


# Utility fixtures
@pytest.fixture
def auth_headers_factory() -> Callable[[str, str], dict[str, str]]:
    """Provide a factory for creating authorization headers.

    Returns:
        Callable: Function to create auth headers
    """

    def _create_auth_headers(token: str, token_type: str = "Bearer") -> dict[str, str]:  # noqa: S107
        return {"Authorization": f"{token_type} {token}"}

    return _create_auth_headers


@pytest.fixture
def invalid_token() -> str:
    """Provide an invalid token for testing.

    Returns:
        str: Invalid token string
    """
    return "invalid.jwt.token"


@pytest.fixture
def expired_token() -> str:
    """Provide an expired token for testing.

    Returns:
        str: Expired token string
    """
    return "expired.jwt.token"


# Mock fixtures for unit testing
@pytest.fixture
def mock_user_store() -> Any:
    """Provide a mock user store for unit testing.

    Returns:
        Mock: Mock user store
    """
    from unittest.mock import AsyncMock, MagicMock

    store = MagicMock()
    store.create_user = AsyncMock()
    store.get_user_by_id = AsyncMock()
    store.get_user_by_username = AsyncMock()
    store.get_user_by_email = AsyncMock()
    store.update_user = AsyncMock()
    store.delete_user = AsyncMock()
    store.list_users = AsyncMock()
    store.count_users = AsyncMock()

    return store


@pytest.fixture
def mock_token_manager() -> Any:
    """Provide a mock token manager for unit testing.

    Returns:
        Mock: Mock token manager
    """
    from unittest.mock import MagicMock

    manager = MagicMock()
    manager.create_token = MagicMock()
    manager.verify_token = MagicMock()
    manager.refresh_token = MagicMock()

    return manager


@pytest.fixture
def mock_auth_provider(mock_user_store: Any, mock_token_manager: Any) -> Any:
    """Provide a mock auth provider for unit testing.

    Args:
        mock_user_store: Mock user store
        mock_token_manager: Mock token manager

    Returns:
        Mock: Mock auth provider
    """
    from unittest.mock import AsyncMock, MagicMock

    provider = MagicMock()
    provider.user_store = mock_user_store
    provider.token_manager = mock_token_manager
    provider.authenticate_user = AsyncMock()
    provider.register_user = AsyncMock()
    provider.create_token = MagicMock()
    provider.verify_token = MagicMock()
    provider.refresh_token = MagicMock()
    provider.get_user = AsyncMock()
    provider.update_user = AsyncMock()
    provider.delete_user = AsyncMock()
    provider.list_users = AsyncMock()
    provider.count_users = AsyncMock()
    provider.has_role = MagicMock()
    provider.has_permission = MagicMock()

    return provider
