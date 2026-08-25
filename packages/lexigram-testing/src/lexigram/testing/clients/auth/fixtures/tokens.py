"""Auth token and authorized request fixtures.

Provides login tokens for the created test users, authorized request
contexts, and token-related utility fixtures.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

import pytest

from lexigram.testing.clients.auth.client import AuthTestClient
from lexigram.testing.clients.auth.fixtures._async import async_fixture
from lexigram.testing.clients.auth.types import AuthTestToken, AuthTestUser


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
    return cast("AuthTestToken", token)


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
    return cast("AuthTestToken", token)


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
    return cast("AuthTestToken", token)


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
    return cast(
        "dict[Any, Any]",
        await auth_test_client.create_authorized_request(created_test_user_admin),
    )


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
    return cast(
        "dict[Any, Any]",
        await auth_test_client.create_authorized_request(created_test_user_regular),
    )


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
    return cast(
        "dict[Any, Any]",
        await auth_test_client.create_authorized_request(created_test_user_moderator),
    )


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
