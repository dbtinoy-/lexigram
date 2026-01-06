"""
AuthProvider adapter for admin user store.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.admin.auth.store.base import AbstractAdminUserStore
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts import AuthenticatedUserProtocol
    from lexigram.contracts.auth.protocols import PasswordHasherProtocol

logger = get_logger(__name__)


@inject
class AuthProviderAdminUserStore(AbstractAdminUserStore):
    """Adapter that delegates admin user operations to an existing AuthProvider.

    This allows the admin subsystem to avoid implementing user lifecycle and
    authentication itself when a canonical AuthProvider (lexigram-auth) is
    available in the application's DI container.

    The adapter expects an AuthProvider instance (which exposes `authenticate_user`,
    `user_store` with `get_user_by_username`, `get_user_by_email`, and `delete_user`).
    """

    def __init__(
        self,
        auth_provider: object,
        password_hasher: PasswordHasherProtocol | None = None,
    ):
        self.auth_provider = auth_provider
        self._password_hasher = password_hasher
        # No local cache; operate directly against auth_provider for canonical behaviour

    async def get_by_id(self, user_id: str) -> AuthenticatedUserProtocol | None:
        # AuthProvider user_store implementations commonly support get_user_by_id
        user_store = getattr(self.auth_provider, "user_store", None)
        if user_store and hasattr(user_store, "get_user_by_id"):
            return await user_store.get_user_by_id(user_id)
        # Fallback to username lookup
        if user_store and hasattr(user_store, "get_user_by_username"):
            return await user_store.get_user_by_username(user_id)
        return None

    async def get_by_email(self, email: str) -> AuthenticatedUserProtocol | None:
        user_store = getattr(self.auth_provider, "user_store", None)
        if user_store and hasattr(user_store, "get_user_by_email"):
            return await user_store.get_user_by_email(email)
        return None

    async def get_by_username(self, username: str) -> AuthenticatedUserProtocol | None:
        user_store = getattr(self.auth_provider, "user_store", None)
        if user_store and hasattr(user_store, "get_user_by_username"):
            return await user_store.get_user_by_username(username)
        return None

    async def authenticate(
        self, email: str, password: str
    ) -> AuthenticatedUserProtocol | None:
        # Prefer provider.authenticate_user (legacy providers) …
        if hasattr(self.auth_provider, "authenticate_user"):
            result = await self.auth_provider.authenticate_user(email, password)
            return result.unwrap_or(None)
        # … or provider.service.authenticate_user (G4-A1.3 split: method lives on AuthenticationService)
        svc = getattr(self.auth_provider, "service", None)
        if svc is not None and hasattr(svc, "authenticate_user"):
            result = await svc.authenticate_user(email, password)
            return result.unwrap_or(None)
        # Fallback to user_store verification if available
        user_store = getattr(self.auth_provider, "user_store", None)
        if user_store and hasattr(user_store, "get_user_by_email"):
            user = await user_store.get_user_by_email(email)
            if not user:
                return None
            hashed = getattr(user, "hashed_password", None)
            if not hashed or self._password_hasher is None:
                return None
            if await self._password_hasher.verify(password, hashed):
                return user
        return None

    async def count(self) -> int:
        """Return the total number of users via the underlying auth provider store."""
        user_store = getattr(self.auth_provider, "user_store", None)
        if user_store:
            # Prefer common count methods used by user stores
            if hasattr(user_store, "count_users"):
                return await user_store.count_users()
            if hasattr(user_store, "count"):
                return await user_store.count()
        return 0
