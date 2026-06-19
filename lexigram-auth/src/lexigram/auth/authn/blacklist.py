"""JWT token blacklist management.

Provides :class:`JWTBlacklist` for revoking individual tokens and all tokens
for a user. Supports both in-process (fallback) and cache-backed storage.

Key schema:
- Individual token: ``jwt:blacklist:{sha256_hex}``
- User-level block:  ``jwt:blacklist:user:{user_id}``
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

import jwt

from lexigram.logging import get_logger
from lexigram.primitives import clock as ambient_clock

if TYPE_CHECKING:
    from lexigram.contracts.audit import AuditLoggerProtocol
    from lexigram.contracts.auth.exceptions import TokenError as ContractsTokenError
    from lexigram.contracts.infra.cache import CacheBackendProtocol
    from lexigram.result import Result

__all__ = ["JWTBlacklist"]

logger = get_logger(__name__)


class JWTBlacklist:
    """Hash-based JWT blacklist supporting both cache and in-process storage.

    When a :class:`~lexigram.contracts.cache.CacheBackendProtocol` is provided,
    revocation entries are persisted with a TTL derived from the token's own
    expiry time.  Without a cache the in-process ``_blacklist`` set is used as
    a fallback (entries are lost on process restart).

    Args:
        cache: Optional cache backend for distributed blacklist storage.
        algorithm: JWT signing algorithm string (used in audit entries).
        current_key_id: Callable that returns the active signing key ID.
        access_expiration_hours: Access token lifetime in hours.
        refresh_expiration_days: Refresh token lifetime in days.
        audit_logger: Optional audit logger for revocation events.
    """

    def __init__(
        self,
        cache: CacheBackendProtocol | None,
        algorithm: str,
        current_key_id_fn: Any,
        access_expiration_hours: int,
        refresh_expiration_days: int,
        audit_logger: AuditLoggerProtocol | None = None,
    ) -> None:
        self._cache = cache
        self._algorithm = algorithm
        self._current_key_id_fn = current_key_id_fn
        self._access_expiration_hours = access_expiration_hours
        self._refresh_expiration_days = refresh_expiration_days
        self._audit_logger = audit_logger
        self._fallback: set[str] = set()

    # ── Public API ────────────────────────────────────────────────────────

    async def revoke(self, token: str) -> Result[None, ContractsTokenError]:
        """Add *token* to the blacklist.

        Args:
            token: The raw JWT string to revoke.

        Returns:
            ``Ok(None)`` on success or if the token is already expired.
            ``Err(TokenError)`` if the cache write fails.

        Raises:
            RuntimeError: On cache-level infrastructure failures.
            OSError: On network-level failures.
            ConnectionError: On connection failures.
        """
        from lexigram.contracts.auth.exceptions import TokenError as ContractsTokenError
        from lexigram.result import Err, Ok

        token_hash = hashlib.sha256(token.encode()).hexdigest()
        cache = self._cache

        if not cache:
            self._fallback.add(token_hash)
            return Ok(None)

        try:
            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            exp = unverified_payload.get("exp", 0)
            now = int(ambient_clock.timestamp())
            ttl = max(0, exp - now)

            if ttl <= 0:
                return Ok(None)

            blacklist_key = f"jwt:blacklist:{token_hash}"
            success = bool(await cache.set(key=blacklist_key, value="1", ttl=ttl))

            if success and self._audit_logger is not None:
                from lexigram.contracts.audit import AuditEntry

                actor_id = str(unverified_payload.get("sub", "unknown"))
                await self._audit_logger.log(
                    AuditEntry(
                        action="token.revoked",
                        actor_id=actor_id,
                        resource_type="Token",
                        resource_id=token_hash[:16],
                        outcome="success",
                        metadata={
                            "algorithm": self._algorithm,
                            "key_id": self._current_key_id_fn(),
                        },
                    )
                )

            return (
                Ok(None)
                if success
                else Err(ContractsTokenError("Token revocation failed"))
            )

        except (RuntimeError, OSError, ConnectionError):
            logger.exception("token_revoke_failed")
            raise

    async def revoke_all_for_user(
        self, user_id: str
    ) -> Result[None, ContractsTokenError]:
        """Blacklist all tokens for *user_id* by writing a user-level sentinel.

        Args:
            user_id: The subject (``sub``) claim of the tokens to revoke.

        Returns:
            ``Ok(None)`` on success. ``Err(TokenError)`` if the write fails.

        Raises:
            RuntimeError: If no cache backend is configured.
        """
        from lexigram.contracts.auth.exceptions import TokenError as ContractsTokenError
        from lexigram.result import Err, Ok

        cache = self._cache
        if not cache:
            raise RuntimeError(
                "Cannot blacklist token: no cache backend configured. "
                "Configure Redis via AuthConfig.cache",
            )

        try:
            blacklist_key = f"jwt:blacklist:user:{user_id}"
            max_token_ttl = max(
                self._access_expiration_hours * 3600,
                self._refresh_expiration_days * 86400,
            )
            success = bool(
                await cache.set(
                    key=blacklist_key,
                    value=int(ambient_clock.timestamp()),
                    ttl=max_token_ttl,
                )
            )
            return (
                Ok(None)
                if success
                else Err(ContractsTokenError("Failed to revoke all user tokens"))
            )
        except (RuntimeError, OSError, ConnectionError):
            logger.exception("token_revoke_all_failed", user_id=user_id)
            raise

    async def is_blacklisted(self, token: str) -> bool:
        """Return ``True`` if *token* has been revoked.

        Checks both the individual token hash and the user-level sentinel.
        Fails closed on cache errors (returns ``True``).

        Args:
            token: The raw JWT string to check.

        Returns:
            ``True`` if the token should be rejected, ``False`` otherwise.
        """
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        cache = self._cache

        if not cache:
            return token_hash in self._fallback

        try:
            if await cache.exists(f"jwt:blacklist:{token_hash}"):
                return True

            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            user_id = unverified_payload.get("sub")
            return bool(user_id and await cache.exists(f"jwt:blacklist:user:{user_id}"))

        except (RuntimeError, OSError, ConnectionError, jwt.InvalidTokenError):
            logger.exception("token_blacklist_check_failed")
            return True  # Fail closed
