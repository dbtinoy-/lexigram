"""Password reset service for Lexigram Auth."""

from __future__ import annotations

from datetime import datetime, timedelta
import secrets
from typing import TYPE_CHECKING, Any

from lexigram.auth.authn.security import PasswordHasher
from lexigram.auth.models.user import UserCredentials
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.primitives import clock as ambient_clock
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.auth.storage.token_store import UserStoreProtocol

logger = get_logger(__name__)


class PasswordResetTokenError(Exception):
    """Error during password reset token operations."""

    _code = "LEX_ERR_AUTH_028"


@inject
class PasswordResetService:
    """Service for handling password reset flows.

    Provides secure password reset with time-limited tokens.
    """

    TOKEN_EXPIRY_HOURS = 24
    TOKEN_LENGTH = 32

    def __init__(
        self,
        user_store: UserStoreProtocol,
        token_ttl_hours: int = TOKEN_EXPIRY_HOURS,
    ) -> None:
        self._store = user_store
        self._token_ttl = timedelta(hours=token_ttl_hours)

    def generate_reset_token(self) -> tuple[str, datetime]:
        """Generate a secure random reset token.

        Returns:
            Tuple of (token, expiry_datetime)
        """
        token = secrets.token_urlsafe(self.TOKEN_LENGTH)
        expiry = (ambient_clock.now()) + self._token_ttl
        return token, expiry

    async def request_reset(
        self, email: str
    ) -> Result[tuple[str, datetime] | None, PasswordResetTokenError]:
        """Request a password reset for a user email.

        Args:
            email: The user's email address.

        Returns:
            ``Ok((token, expiry))`` when the user exists and a token was created.
            ``Ok(None)`` when no user with that email exists (silent, prevents
            email enumeration).
            ``Err(PasswordResetTokenError)`` on store failure.
        """
        user = await self._store.get_user_by_email(email)

        if not user:
            logger.debug("Password reset requested for non-existent email: %s", email)
            return Ok(None)

        token, expiry = self.generate_reset_token()

        await self._store.update_user(user)

        logger.info("Password reset token generated for user: %s", user.user_id)
        return Ok((token, expiry))

    async def confirm_reset(
        self, token: str, new_password: str
    ) -> Result[None, PasswordResetTokenError]:
        """Confirm password reset with new password.

        Args:
            token: The reset token.
            new_password: The new password to set.

        Returns:
            ``Ok(None)`` when the reset succeeded.
            ``Err(PasswordResetTokenError)`` when the token is invalid or expired.
        """
        user = await self._find_user_by_token(token)

        if not user:
            logger.warning("Invalid password reset token used")
            return Err(PasswordResetTokenError("Invalid or expired reset token"))

        hasher = PasswordHasher()
        hashed_password = await hasher.hash(new_password)

        new_creds = UserCredentials(
            user_id=user.user_id,
            hashed_password=hashed_password,
        )
        await self._store.update_credentials(new_creds)

        logger.info("Password reset completed for user: %s", user.user_id)
        return Ok(None)

    async def _find_user_by_token(self, token: str) -> Any | None:
        """Find user by reset token."""
        users = await self._store.list_users(skip=0, limit=1000)

        for user in users:
            if (
                hasattr(user, "password_reset_token")
                and user.password_reset_token == token
            ):
                if hasattr(user, "password_reset_expires_at") and (
                    user.password_reset_expires_at
                    and user.password_reset_expires_at > (ambient_clock.now())
                ):
                    return user
                break

        return None

    async def invalidate_token(self, user_id: str) -> None:
        """Invalidate any pending reset token for a user."""
        user = await self._store.get_user_by_id(user_id)

        if user:
            user.password_reset_token = None  # type: ignore[attr-defined]
            user.password_reset_expires_at = None  # type: ignore[attr-defined]
            await self._store.update_user(user)

    def __repr__(self) -> str:
        return f"PasswordResetService(user_store={type(self._store).__name__})"


__all__ = [
    "PasswordResetService",
    "PasswordResetTokenError",
    "logger",
]
