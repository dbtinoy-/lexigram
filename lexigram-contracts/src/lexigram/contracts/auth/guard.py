"""GuardProtocol and authentication protocols.

Protocols for authentication and authorization middleware.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AuthenticatorProtocol(Protocol):
    """Protocol for request authentication.

    Authenticators extract and validate credentials from requests.
    """

    async def authenticate(self, request: Any) -> Any | None:
        """Authenticate a request.

        Args:
            request: The incoming request.

        Returns:
            Authenticated user if valid, None otherwise.
        """
        ...


@runtime_checkable
class AuthorizerProtocol(Protocol):
    """Protocol for authorization decisions.

    Authorizers determine if an authenticated user can perform
    a specific action on a resource.
    """

    async def authorize(
        self,
        user: Any,
        action: str,
        resource: Any,
    ) -> bool:
        """Check if user is authorized for action on resource.

        Args:
            user: Authenticated user.
            action: Action to perform (e.g., "read", "write", "delete").
            resource: Target resource.

        Returns:
            True if authorized.
        """
        ...

    async def check_access(
        self,
        user: Any,
        allowed_roles: set[str],
        resource: str | None = None,
        action: str | None = None,
    ) -> bool:
        """Check if user has access based on roles and permissions.

        Args:
            user: Authenticated user.
            allowed_roles: Set of roles that grant access.
            resource: Target resource (optional).
            action: Action to perform (optional).

        Returns:
            True if access is granted.
        """
        ...

    async def can(self, user: Any, action: str, resource: str) -> bool:
        """Check if user can perform action on resource.

        Args:
            user: Authenticated user.
            action: Action to perform.
            resource: Target resource.

        Returns:
            True if authorized.
        """
        ...


__all__ = ["AuthenticatorProtocol", "AuthorizerProtocol"]
