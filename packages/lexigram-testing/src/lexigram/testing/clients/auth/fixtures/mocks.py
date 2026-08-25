"""Mock fixtures for unit-testing lexigram-auth components in isolation.

Provides mock user store, token manager, and auth provider doubles.
"""

from __future__ import annotations

from typing import Any

import pytest


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
