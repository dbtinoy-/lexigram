"""Shared pytest fixtures for lexigram-example-api tests.

Provides mock repository and event publisher factories that satisfy
the relevant Protocol interfaces without touching real infrastructure.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram_example_api.repositories.todo_repository import InMemoryTodoRepository
from lexigram_example_api.repositories.user_repository import InMemoryUserRepository


@pytest.fixture
def user_repo() -> InMemoryUserRepository:
    """Return a fresh in-memory user repository.

    Returns:
        Empty :class:`~lexigram_example_api.repositories.user_repository.InMemoryUserRepository`.
    """
    return InMemoryUserRepository()


@pytest.fixture
def todo_repo() -> InMemoryTodoRepository:
    """Return a fresh in-memory todo repository.

    Returns:
        Empty :class:`~lexigram_example_api.repositories.todo_repository.InMemoryTodoRepository`.
    """
    return InMemoryTodoRepository()


@pytest.fixture
def mock_event_publisher() -> MagicMock:
    """Return a mock that satisfies :class:`~lexigram.contracts.events.protocols.DomainEventPublisherProtocol`.

    Returns:
        ``AsyncMock``-powered publisher that records ``publish`` calls.
    """
    publisher = MagicMock()
    publisher.publish = AsyncMock(return_value=None)
    return publisher


@pytest.fixture
def mock_hasher() -> MagicMock:
    """Return a mock PasswordHasher with predictable hash/verify behaviour.

    ``hash(p)`` returns ``"hashed::" + p``.
    ``verify(p, h)`` returns ``True`` when ``h == "hashed::" + p``.

    Returns:
        Mock that mimics the :class:`~lexigram.auth.authn.security.PasswordHasher` API.
    """
    hasher = MagicMock()
    hasher.hash = AsyncMock(side_effect=lambda p: f"hashed::{p}")
    hasher.verify = AsyncMock(side_effect=lambda p, h: h == f"hashed::{p}")
    return hasher


@pytest.fixture
def mock_jwt_manager() -> MagicMock:
    """Return a mock JWTTokenManager that creates predictable tokens.

    ``create_access_token(user)`` returns ``"token::" + user.user_id``.

    Returns:
        Mock that mimics the :class:`~lexigram.auth.authn.jwt.JWTTokenManager` API.
    """
    manager = MagicMock()
    manager.create_access_token = MagicMock(
        side_effect=lambda user: f"token::{user.user_id}"
    )
    manager.verify_token = AsyncMock()
    return manager
