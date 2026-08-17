"""
Base admin user store interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.contracts.auth import AuthenticatedUserProtocol


class AbstractAdminUserStore(ABC):
    """Abstract base class for admin user stores.

    Provides the interface for admin user operations including
    authentication, user lookup, and user management.
    """

    @abstractmethod
    async def get_by_id(self, user_id: str) -> AuthenticatedUserProtocol | None:
        """Get user by ID."""
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> AuthenticatedUserProtocol | None:
        """Get user by email address."""
        ...

    @abstractmethod
    async def get_by_username(self, username: str) -> AuthenticatedUserProtocol | None:
        """Get user by username."""
        ...

    @abstractmethod
    async def authenticate(
        self, email: str, password: str
    ) -> AuthenticatedUserProtocol | None:
        """Authenticate user by email and password."""
        ...

    @abstractmethod
    async def count(self) -> int:
        """Get total number of users."""
        ...


__all__ = ["AbstractAdminUserStore"]
