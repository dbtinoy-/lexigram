"""Auth test user fixtures.

Provides user template fixtures, fixtures that create those users in the
system under test, and bulk multi-user fixtures.
"""

from __future__ import annotations

from typing import Any, cast

import pytest

from lexigram.testing.clients.auth.client import AuthTestClient
from lexigram.testing.clients.auth.fixtures._async import async_fixture
from lexigram.testing.clients.auth.types import AuthTestUser


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
    return cast(
        "AuthTestUser",
        await auth_test_client.create_test_user(
            username=test_user_admin.username,
            email=test_user_admin.email,
            password=test_user_admin.password,
            roles=test_user_admin.roles,
            permissions=test_user_admin.permissions,
        ),
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
    return cast(
        "AuthTestUser",
        await auth_test_client.create_test_user(
            username=test_user_regular.username,
            email=test_user_regular.email,
            password=test_user_regular.password,
            roles=test_user_regular.roles,
            permissions=test_user_regular.permissions,
        ),
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
    return cast(
        "AuthTestUser",
        await auth_test_client.create_test_user(
            username=test_user_moderator.username,
            email=test_user_moderator.email,
            password=test_user_moderator.password,
            roles=test_user_moderator.roles,
            permissions=test_user_moderator.permissions,
        ),
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
    return cast(
        "AuthTestUser",
        await auth_test_client.create_test_user(
            username=test_user_inactive.username,
            email=test_user_inactive.email,
            password=test_user_inactive.password,
            roles=test_user_inactive.roles,
            permissions=test_user_inactive.permissions,
            is_active=test_user_inactive.is_active,
        ),
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
    return cast(
        "AuthTestUser",
        await auth_test_client.create_test_user(
            username=test_user_unverified.username,
            email=test_user_unverified.email,
            password=test_user_unverified.password,
            roles=test_user_unverified.roles,
            permissions=test_user_unverified.permissions,
            is_verified=test_user_unverified.is_verified,
        ),
    )


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
