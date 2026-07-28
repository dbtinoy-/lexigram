"""Subscription authentication hooks.

Provides connection-level authentication for WebSocket subscriptions.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from lexigram.graphql.exceptions import AuthenticationError

# Type for connection auth hook
ConnectionAuthHook = Callable[[dict[str, Any]], Awaitable[bool]]


class SubscriptionAuth:
    """Handles authentication for WebSocket subscriptions.

    Provides hooks for validating connection tokens during connection_init.
    """

    def __init__(
        self,
        on_auth: ConnectionAuthHook | None = None,
    ):
        """Initialize the subscription auth handler.

        Args:
            on_auth: Optional async callback to validate auth payload.
                     Should return True if authentication succeeds.
        """
        self._on_auth = on_auth

    async def authenticate(self, payload: dict[str, Any]) -> bool:
        """Authenticate a connection_init payload.

        Args:
            payload: The payload from the connection_init message.

        Returns:
            True if authentication succeeds.

        Raises:
            AuthenticationError: If authentication fails.
        """
        if self._on_auth is None:
            # No auth hook - allow all connections
            return True

        try:
            result = await self._on_auth(payload)
            if not result:
                raise AuthenticationError("Authentication failed")
            return result
        except AuthenticationError:
            raise
        except (TypeError, ValueError, RuntimeError) as e:
            raise AuthenticationError(f"Authentication error: {e}") from e

    def set_auth_hook(self, hook: ConnectionAuthHook) -> None:
        """Set the authentication hook.

        Args:
            hook: Async callback to validate auth payload.
        """
        self._on_auth = hook


# Default auth instance
default_auth = SubscriptionAuth()


__all__ = ["ConnectionAuthHook", "SubscriptionAuth", "default_auth"]
