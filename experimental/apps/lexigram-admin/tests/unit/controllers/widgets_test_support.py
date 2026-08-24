"""Shared test helpers for widget controller tests."""

from __future__ import annotations

from unittest.mock import MagicMock


def _user_with_permissions(*permissions: str) -> MagicMock:
    """Build a user mock with the given permission set and no roles."""
    user = MagicMock()
    user.permissions = frozenset(permissions)
    user.roles = frozenset()
    return user


def _request_for(user: MagicMock) -> MagicMock:
    """Build a request mock carrying the given user on state."""
    request = MagicMock()
    request.query_params = {}
    state = MagicMock()
    state.user = user
    request.state = state
    return request
