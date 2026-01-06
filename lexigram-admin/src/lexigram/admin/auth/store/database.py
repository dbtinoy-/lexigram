"""
Database-backed admin user store implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.admin.auth.store.base import AbstractAdminUserStore
from lexigram.admin.exceptions import AdminDataError
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.admin.auth.entity import AdminUserEntity
    from lexigram.contracts import AuthenticatedUserProtocol, RepositoryProtocol
    from lexigram.contracts.auth import PasswordHasherProtocol
from lexigram.di.decorators import inject

logger = get_logger(__name__)


@inject
class DatabaseAdminUserStore(AbstractAdminUserStore):
    """Database-backed store for admin users.

    Uses a repository to fetch and authenticate users from admin_users table.
    """

    def __init__(
        self,
        repository: RepositoryProtocol[AdminUserEntity],
        hasher: PasswordHasherProtocol | None = None,
    ):
        """Initialize with repository.

        Args:
            repository: RepositoryProtocol for AdminUserEntity
            hasher: Optional password hasher for authentication
        """
        self.repo = repository
        self._hasher = hasher

    async def get_by_id(self, user_id: str) -> AuthenticatedUserProtocol | None:
        """Get user by id via repository and convert to `User`."""
        try:
            entity = await self.repo.find_by_id(user_id)  # type: ignore[attr-defined]
            if entity is None:
                return None
            # Convert DB entity to User dataclass
            if hasattr(entity, "to_user"):
                return entity.to_user()
            return entity
        except (ConnectionError, RuntimeError, ValueError, OSError) as e:
            raise AdminDataError(f"Failed to retrieve user {user_id}: {e}") from e

    async def get_by_email(self, email: str) -> AuthenticatedUserProtocol | None:
        """Get user by email via repository and convert to `User`."""
        try:
            entity = await self.repo.find_one(email=email)  # type: ignore[attr-defined]
            if entity is None:
                return None
            if hasattr(entity, "to_user"):
                return entity.to_user()
            return entity
        except (ConnectionError, RuntimeError, ValueError, OSError) as e:
            raise AdminDataError(f"Failed to find user by email: {e}") from e

    async def get_by_username(self, username: str) -> AuthenticatedUserProtocol | None:
        """Get user by username via repository and convert to `User`."""
        try:
            entity = await self.repo.find_one(username=username)  # type: ignore[attr-defined]
            if entity is None:
                return None
            if hasattr(entity, "to_user"):
                return entity.to_user()
            return entity
        except (ConnectionError, RuntimeError, ValueError, OSError) as e:
            raise AdminDataError(f"Failed to find user by username: {e}") from e

    async def authenticate(
        self, email: str, password: str
    ) -> AuthenticatedUserProtocol | None:
        """Authenticate user by email/password using DB repository."""
        user = await self.get_by_email(email)
        if not user:
            return None

        if not getattr(user, "is_active", True):
            return None

        hashed = getattr(user, "hashed_password", None)
        if not hashed:
            return None

        try:
            if self._hasher:
                if await self._hasher.verify(password, hashed):
                    return user
            else:
                import hashlib

                if hashlib.sha256(password.encode()).hexdigest() == hashed:
                    return user
        except (ValueError, RuntimeError, OSError) as e:
            raise AdminDataError(
                f"Authentication verification failed for {email}: {e}"
            ) from e

        return None

    async def count(self) -> int:
        """Return total users via repo.count()."""
        try:
            return await self.repo.count()
        except (ConnectionError, RuntimeError, OSError) as e:
            raise AdminDataError(f"Failed to count users: {e}") from e
