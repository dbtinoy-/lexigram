"""Admin session lifecycle management service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import secrets
from typing import Any

from lexigram.admin.auth.protocols import AdminSessionServiceProtocol
from lexigram.contracts.auth.repositories import SessionRepositoryProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.serialization import dumps
from lexigram.serialization.backends.json import loads as _json_loads

logger = get_logger(__name__)


@inject
class AdminSessionService:
    """Admin session lifecycle management service.

    Wraps ``SessionRepositoryProtocol`` to handle creation, idle-timeout
    enforcement, absolute-expiry enforcement, activity tracking, and
    single/bulk revocation.

    The ``fingerprint`` column in the underlying ``admin_sessions`` table is
    used to carry ``email`` and ``roles`` as a JSON-serialisable dict.
    PostgreSQL stores this as JSONB (auto-parsed on read); SQLite stores it
    as TEXT, which this service parses back to a dict transparently.

    The ``fingerprint_sig`` column stores an HMAC-SHA256 signature of the
    fingerprint JSON to detect tampering (AUTH-05).
    """

    def __init__(
        self,
        session_repo: SessionRepositoryProtocol,
        session_lifetime: int = 86400,
        idle_timeout: int = 3600,
        fingerprint_secret: str = "",
    ) -> None:
        """Initialize with repository and lifetime configuration.

        Args:
            session_repo: Repository that satisfies
                ``SessionRepositoryProtocol`` from ``lexigram-contracts``.
            session_lifetime: Absolute session lifetime in seconds
                (default 86 400 = 24 h).
            idle_timeout: Idle inactivity timeout in seconds
                (default 3 600 = 1 h). A session that has not been
                touched within this window is treated as expired.
            fingerprint_secret: HMAC key for fingerprint signing.
                When empty, signing is skipped (backward compatibility).
        """
        self._repo = session_repo
        self._session_lifetime = session_lifetime
        self._idle_timeout = idle_timeout
        self._fingerprint_key: bytes = (
            hashlib.sha256(fingerprint_secret.encode()).digest()
            if fingerprint_secret
            else b""
        )
        self._signing_enabled = bool(fingerprint_secret)

    # ------------------------------------------------------------------
    # AdminSessionServiceProtocol
    # ------------------------------------------------------------------

    async def create_session(
        self,
        user_id: str,
        email: str,
        roles: list[str],
        ip_address: str,
        user_agent: str,
    ) -> str:
        """Create a new session and return the session ID.

        Generates a cryptographically secure session identifier, persists
        the session with absolute expiry and initial last-active timestamp,
        and stores ``email`` and ``roles`` in the ``fingerprint`` column so
        that they can be retrieved without a secondary user-table lookup.

        When ``fingerprint_secret`` is configured, the fingerprint JSON is
        HMAC-SHA256 signed and the signature stored in ``fingerprint_sig``.

        Args:
            user_id: Admin user UUID.
            email: Admin user email.
            roles: User's role names.
            ip_address: Client IP address.
            user_agent: Client user agent string.

        Returns:
            New session identifier (``secrets.token_urlsafe(32)``).
        """
        session_id = secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=self._session_lifetime)

        fingerprint: dict[str, Any] = {"email": email, "roles": roles}

        payload: dict[str, Any] = {
            "session_id": session_id,
            "admin_id": user_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "fingerprint": fingerprint,
            "expires_at": expires_at,
            "created_at": now,
            "last_active_at": now,
        }

        if self._signing_enabled:
            payload["fingerprint_sig"] = self._sign_fingerprint(fingerprint)

        await self._repo.insert(payload)
        logger.info(
            "session.created",
            session_id=session_id,
            user_id=user_id,
            expires_at=expires_at.isoformat(),
        )
        return session_id

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve session data if valid (not expired, not revoked).

        Checks absolute expiry first, then idle timeout. Either condition
        triggers an immediate revocation of the session record so that
        subsequent requests cannot use it even if the ``is_active`` flag
        would otherwise still be TRUE.

        When ``fingerprint_secret`` is configured, the fingerprint signature
        is verified on read. A mismatch causes immediate revocation.

        Args:
            session_id: Session to retrieve.

        Returns:
            Session data dict (including parsed ``fingerprint``) or ``None``
            if the session does not exist, is revoked, or has expired.
        """
        row = await self._repo.find_active(session_id)
        if row is None:
            return None

        now = datetime.now(UTC)

        # --- Absolute expiry check ---
        expires_at = _parse_dt(row.get("expires_at"))
        if expires_at is not None and expires_at <= now:
            await self._repo.revoke(session_id)
            logger.debug("session.expired_absolute", session_id=session_id)
            return None

        # --- Idle timeout check ---
        last_active_at = _parse_dt(row.get("last_active_at"))
        if last_active_at is not None:
            idle_deadline = last_active_at + timedelta(seconds=self._idle_timeout)
            if idle_deadline <= now:
                await self._repo.revoke(session_id)
                logger.debug("session.expired_idle", session_id=session_id)
                return None

        # Return a copy with fingerprint normalised to a dict regardless of
        # whether the underlying store returned it as JSONB (already dict) or
        # TEXT (requires JSON parsing — SQLite path).
        result = dict(row)
        fingerprint = result.get("fingerprint")
        if isinstance(fingerprint, str):
            try:
                result["fingerprint"] = _json_loads(fingerprint)
            except (ValueError, TypeError):
                result["fingerprint"] = {}

        # --- Fingerprint HMAC verification (AUTH-05) ---
        if self._signing_enabled:
            stored_sig: str | None = result.get("fingerprint_sig")
            if not stored_sig or not self._verify_fingerprint(
                result["fingerprint"], stored_sig
            ):
                logger.warning(
                    "session.fingerprint_tampered",
                    session_id=session_id,
                )
                await self._repo.revoke(session_id)
                return None

        return result

    # ------------------------------------------------------------------
    # Fingerprint HMAC helpers (AUTH-05)
    # ------------------------------------------------------------------

    def _sign_fingerprint(self, fingerprint: dict[str, Any]) -> str:
        """HMAC-SHA256 sign the fingerprint dict.

        Args:
            fingerprint: Fingerprint dict (email, roles).

        Returns:
            Hex-encoded HMAC-SHA256 signature.
        """
        raw = dumps(fingerprint, sort_keys=True)
        return hmac.new(self._fingerprint_key, raw, hashlib.sha256).hexdigest()

    def _verify_fingerprint(self, fingerprint: dict[str, Any], signature: str) -> bool:
        """Verify the HMAC-SHA256 signature of a fingerprint.

        Args:
            fingerprint: Fingerprint dict to verify.
            signature: Previously stored hex-encoded signature.

        Returns:
            True if the signature matches, False otherwise.
        """
        expected = self._sign_fingerprint(fingerprint)
        return hmac.compare_digest(expected, signature)

    # ------------------------------------------------------------------
    # Touch / revoke
    # ------------------------------------------------------------------

    async def touch_session(self, session_id: str) -> None:
        """Update session last-active timestamp to now (UTC).

        Args:
            session_id: Session to touch.
        """
        now = datetime.now(UTC)
        await self._repo.update_activity(session_id, now)
        logger.debug("session.touched", session_id=session_id)

    async def revoke_session(self, session_id: str) -> None:
        """Revoke a single session (logout).

        Args:
            session_id: Session to revoke.
        """
        await self._repo.revoke(session_id)
        logger.info("session.revoked", session_id=session_id)

    async def revoke_all_user_sessions(self, user_id: str) -> None:
        """Revoke all active sessions for a user.

        Delegates to the repository's ``revoke_all`` which issues a single
        bulk UPDATE rather than fetching and revoking sessions individually.

        Args:
            user_id: Admin user UUID whose sessions are to be revoked.
        """
        await self._repo.revoke_all(user_id)
        logger.info("session.revoked_all", user_id=user_id)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _parse_dt(value: Any) -> datetime | None:
    """Parse a datetime from a DB row value.

    Handles both timezone-aware ``datetime`` objects returned by async
    PostgreSQL drivers (e.g. asyncpg) and ISO-8601 strings returned by
    SQLite drivers.  Naïve datetimes are assumed to be UTC.

    Args:
        value: Raw column value from the database row.

    Returns:
        Timezone-aware ``datetime`` in UTC, or ``None`` if ``value`` is
        ``None`` or cannot be parsed.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt
        except ValueError:
            return None
    return None


# Verify structural subtyping at import time: AdminSessionService must
# satisfy AdminSessionServiceProtocol without explicit inheritance.
_: AdminSessionServiceProtocol = AdminSessionService.__new__(AdminSessionService)

__all__ = ["AdminSessionService"]
