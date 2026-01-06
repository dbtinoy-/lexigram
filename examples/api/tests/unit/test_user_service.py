"""Unit tests for UserService.

Tests exercise the service through its Protocol contracts — no real
infrastructure (DB, cache, JWT server) is used.  All dependencies are
mocked at the protocol boundary.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lexigram_example_api.domain.user import User
from lexigram_example_api.repositories.user_repository import InMemoryUserRepository
from lexigram_example_api.services.user_service import (
    EmailAlreadyRegistered,
    InvalidCredentials,
    UserService,
)


def _make_service(
    user_repo: InMemoryUserRepository,
    mock_hasher: MagicMock,
    mock_jwt_manager: MagicMock,
    mock_event_publisher: MagicMock,
) -> UserService:
    """Factory that wires a UserService from test doubles.

    Args:
        user_repo: In-memory user repository.
        mock_hasher: Mock password hasher.
        mock_jwt_manager: Mock JWT token manager.
        mock_event_publisher: Mock event publisher.

    Returns:
        Configured :class:`~lexigram_example_api.services.user_service.UserService`.
    """
    return UserService(
        repo=user_repo,
        hasher=mock_hasher,
        jwt_manager=mock_jwt_manager,
        event_publisher=mock_event_publisher,
    )


class TestUserServiceRegister:
    """Tests for UserService.register."""

    @pytest.mark.asyncio
    async def test_register_success_returns_ok_user(
        self,
        user_repo: InMemoryUserRepository,
        mock_hasher: MagicMock,
        mock_jwt_manager: MagicMock,
        mock_event_publisher: MagicMock,
    ) -> None:
        """Successful registration returns Ok with the persisted user."""
        service = _make_service(
            user_repo, mock_hasher, mock_jwt_manager, mock_event_publisher
        )

        result = await service.register("alice@example.com", "secret123")

        assert result.is_ok()
        user = result.unwrap()
        assert user.email == "alice@example.com"
        assert user.user_id != ""
        assert user.hashed_password == "hashed::secret123"

    @pytest.mark.asyncio
    async def test_register_publishes_user_created_event(
        self,
        user_repo: InMemoryUserRepository,
        mock_hasher: MagicMock,
        mock_jwt_manager: MagicMock,
        mock_event_publisher: MagicMock,
    ) -> None:
        """A UserCreated domain event is published after registration."""
        service = _make_service(
            user_repo, mock_hasher, mock_jwt_manager, mock_event_publisher
        )

        await service.register("bob@example.com", "password99")

        mock_event_publisher.publish.assert_called_once()
        event = mock_event_publisher.publish.call_args[0][0]
        assert type(event).__name__ == "UserCreated"
        assert event.email == "bob@example.com"

    @pytest.mark.asyncio
    async def test_register_duplicate_email_returns_err(
        self,
        user_repo: InMemoryUserRepository,
        mock_hasher: MagicMock,
        mock_jwt_manager: MagicMock,
        mock_event_publisher: MagicMock,
    ) -> None:
        """Registering with an existing email returns Err(EmailAlreadyRegistered)."""
        service = _make_service(
            user_repo, mock_hasher, mock_jwt_manager, mock_event_publisher
        )

        await service.register("carol@example.com", "password123")
        result = await service.register("carol@example.com", "different123")

        assert result.is_err()
        assert isinstance(result.unwrap_err(), EmailAlreadyRegistered)
        assert result.unwrap_err().email == "carol@example.com"

    @pytest.mark.asyncio
    async def test_register_email_normalised_to_lowercase(
        self,
        user_repo: InMemoryUserRepository,
        mock_hasher: MagicMock,
        mock_jwt_manager: MagicMock,
        mock_event_publisher: MagicMock,
    ) -> None:
        """Email addresses are stored and compared in lowercase."""
        service = _make_service(
            user_repo, mock_hasher, mock_jwt_manager, mock_event_publisher
        )

        result = await service.register("Alice@Example.COM", "password123")

        assert result.is_ok()
        assert result.unwrap().email == "alice@example.com"


class TestUserServiceAuthenticate:
    """Tests for UserService.authenticate."""

    @pytest.mark.asyncio
    async def test_authenticate_valid_credentials_returns_token(
        self,
        user_repo: InMemoryUserRepository,
        mock_hasher: MagicMock,
        mock_jwt_manager: MagicMock,
        mock_event_publisher: MagicMock,
    ) -> None:
        """Correct credentials produce an Ok result containing a JWT string."""
        service = _make_service(
            user_repo, mock_hasher, mock_jwt_manager, mock_event_publisher
        )
        await service.register("dave@example.com", "correctpass")

        result = await service.authenticate("dave@example.com", "correctpass")

        assert result.is_ok()
        token = result.unwrap()
        assert token.startswith("token::")

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password_returns_err(
        self,
        user_repo: InMemoryUserRepository,
        mock_hasher: MagicMock,
        mock_jwt_manager: MagicMock,
        mock_event_publisher: MagicMock,
    ) -> None:
        """Wrong password returns Err(InvalidCredentials)."""
        service = _make_service(
            user_repo, mock_hasher, mock_jwt_manager, mock_event_publisher
        )
        await service.register("eve@example.com", "correctpass")

        result = await service.authenticate("eve@example.com", "wrongpass")

        assert result.is_err()
        assert isinstance(result.unwrap_err(), InvalidCredentials)

    @pytest.mark.asyncio
    async def test_authenticate_unknown_email_returns_err(
        self,
        user_repo: InMemoryUserRepository,
        mock_hasher: MagicMock,
        mock_jwt_manager: MagicMock,
        mock_event_publisher: MagicMock,
    ) -> None:
        """Unknown email returns Err(InvalidCredentials) — no email enumeration."""
        service = _make_service(
            user_repo, mock_hasher, mock_jwt_manager, mock_event_publisher
        )

        result = await service.authenticate("nobody@example.com", "anypass")

        assert result.is_err()
        assert isinstance(result.unwrap_err(), InvalidCredentials)


class TestUserServiceFindById:
    """Tests for UserService.find_by_id."""

    @pytest.mark.asyncio
    async def test_find_by_id_existing_user_returns_ok(
        self,
        user_repo: InMemoryUserRepository,
        mock_hasher: MagicMock,
        mock_jwt_manager: MagicMock,
        mock_event_publisher: MagicMock,
    ) -> None:
        """Finding an existing user returns Ok(User)."""
        service = _make_service(
            user_repo, mock_hasher, mock_jwt_manager, mock_event_publisher
        )
        reg_result = await service.register("frank@example.com", "password123")
        user = reg_result.unwrap()

        result = await service.find_by_id(user.user_id)

        assert result.is_ok()
        assert result.unwrap().user_id == user.user_id

    @pytest.mark.asyncio
    async def test_find_by_id_missing_user_returns_err(
        self,
        user_repo: InMemoryUserRepository,
        mock_hasher: MagicMock,
        mock_jwt_manager: MagicMock,
        mock_event_publisher: MagicMock,
    ) -> None:
        """Finding a non-existent user returns Err(NotFoundError)."""
        from lexigram.contracts.exceptions.domain import NotFoundError

        service = _make_service(
            user_repo, mock_hasher, mock_jwt_manager, mock_event_publisher
        )

        result = await service.find_by_id("nonexistent-id")

        assert result.is_err()
        assert isinstance(result.unwrap_err(), NotFoundError)
