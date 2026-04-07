"""
In-memory admin user store implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.admin.auth.store.base import AbstractAdminUserStore
from lexigram.admin.auth.user import AdminUserRecord
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts import AuthenticatedUserProtocol
    from lexigram.contracts.auth import PasswordHasherProtocol
from lexigram.di.decorators import inject

logger = get_logger(__name__)


@inject
class MemoryAdminUserStore(AbstractAdminUserStore):
    """In-memory store for admin users with authentication support.

    Attributes:
        _users_by_id: Dictionary of users by ID
        _users_by_email: Dictionary of users by email
        _users_by_username: Dictionary of users by username
    """

    def __init__(self, config: Any, hasher: PasswordHasherProtocol | None = None):
        """Initialize user store from configuration."""
        self._hasher = hasher
        self._users_by_id: dict[str, AdminUserRecord] = {}
        self._users_by_email: dict[str, AdminUserRecord] = {}
        self._users_by_username: dict[str, AdminUserRecord] = {}

        # Handle both legacy and modern Pydantic config
        users = getattr(config, "users", [])

        # Load users from config
        for user_data in users:
            # Check if it's a Pydantic model (modern config)
            if hasattr(user_data, "model_dump"):
                # Map AuthUserConfig to User
                user = AdminUserRecord(
                    user_id=user_data.username,
                    name=user_data.username,
                    email=user_data.email,
                    hashed_password=user_data.password_hash
                    or user_data.password,  # Very basic mapping
                    roles=user_data.roles,
                    permissions=[],  # Needs flattening from roles if strictly mimicking legacy
                    is_active=user_data.is_active,
                    is_verified=True,
                )
            elif isinstance(user_data, dict):
                # Map dict to AdminUserRecord
                user = AdminUserRecord(
                    user_id=user_data.get("username", ""),
                    name=user_data.get("username", ""),
                    email=user_data.get("email", ""),
                    hashed_password=user_data.get("password_hash")
                    or user_data.get("password"),
                    roles=user_data.get("roles", []),
                    permissions=user_data.get("permissions", []),
                    is_active=user_data.get("is_active", True),
                    is_verified=True,
                )
            else:
                user = user_data

            # Safe ID extraction
            user_id = getattr(user, "user_id", None)
            if not user_id:
                user_id = getattr(user, "username", "")

            if user_id:
                self._users_by_id[user_id] = user

            email = getattr(user, "email", "")
            if email:
                self._users_by_email[email.lower()] = user

            username = getattr(user, "username", "")
            if username:
                self._users_by_username[username.lower()] = user

    async def get_by_id(self, user_id: str) -> AuthenticatedUserProtocol | None:
        """Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User if found, None otherwise
        """
        return self._users_by_id.get(user_id)

    async def get_by_email(self, email: str) -> AuthenticatedUserProtocol | None:
        """Get user by email address.

        Args:
            email: Email address (case-insensitive)

        Returns:
            User if found, None otherwise
        """
        return self._users_by_email.get(email.lower())

    async def get_by_username(self, username: str) -> AuthenticatedUserProtocol | None:
        """Get user by username.

        Args:
            username: Username (case-insensitive)

        Returns:
            User if found, None otherwise
        """
        return self._users_by_username.get(username.lower())

    async def authenticate(
        self, email: str, password: str
    ) -> AuthenticatedUserProtocol | None:
        """Authenticate user by email and password.

        Args:
            email: Email address
            password: Plain text password

        Returns:
            User if authentication successful, None otherwise
        """
        user = await self.get_by_email(email)

        if not user:
            return None

        if not user.is_active:
            return None

        if not user.hashed_password:  # type: ignore[attr-defined]
            return None
        if self._hasher:
            verified = await self._hasher.verify(password, user.hashed_password)  # type: ignore[attr-defined]
        else:
            import hashlib

            verified = (
                hashlib.sha256(password.encode()).hexdigest() == user.hashed_password  # type: ignore[attr-defined]
            )
        if not verified:
            return None

        return user

    async def count(self) -> int:
        """Get total number of users.

        Returns:
            Number of users in store
        """
        return len(self._users_by_id)
