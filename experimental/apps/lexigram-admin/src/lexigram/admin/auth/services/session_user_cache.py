"""Short-TTL in-process cache for the per-request session→user lookup.

Every authenticated admin request resolves the signed session cookie to an
``AdminUser`` via two sequential DB round-trips (``admin_sessions`` +
``admin_users``). HTMX-heavy pages fire bursts of requests, so the pair is
paid many times per page render. ``SessionUserCache`` short-circuits the
pair for a short, configurable window (default 5 seconds).

Security posture (see docs/09-01-2026/12-session-user-cache.md):

- All revocation flows funnel through ``AdminSessionService.revoke_session``
  / ``revoke_all_user_sessions``, and both invalidate this cache — so
  same-process revocation takes effect immediately. The TTL only bounds
  staleness across *other* workers in multi-process deployments.
- Guests and lookup failures are never cached (no negative caching).
- The cache is size-bounded; overflow evicts the oldest entry, so a
  session-flooding attempt cannot grow memory without bound.
- ``ttl_seconds=0`` disables the cache entirely (get always misses, put is
  a no-op) for operators who cannot accept any staleness window.
"""

from __future__ import annotations

from collections.abc import Callable
import time
from typing import TYPE_CHECKING

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts import AuthenticatedUserProtocol

logger = get_logger(__name__)

DEFAULT_TTL_SECONDS = 5.0
DEFAULT_MAX_ENTRIES = 512


class SessionUserCache:
    """Bounded, short-TTL map of ``session_id`` → authenticated user.

    Pure in-process dict operations on the event loop: no I/O, no locks.
    Entries expire lazily on read; inserts evict the oldest entry once
    ``max_entries`` is reached.
    """

    def __init__(
        self,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        max_entries: int = DEFAULT_MAX_ENTRIES,
        time_source: Callable[[], float] = time.monotonic,
    ) -> None:
        """Initialize the cache.

        Args:
            ttl_seconds: How long a cached entry stays valid. ``0`` (or
                negative) disables the cache: ``get`` always misses and
                ``put`` is a no-op.
            max_entries: Hard upper bound on stored entries; the oldest
                entry is evicted when a put would exceed it.
            time_source: Monotonic clock, injectable for tests.
        """
        self._ttl = float(ttl_seconds)
        self._max_entries = max(1, int(max_entries))
        self._now = time_source
        # session_id -> (user, user_id, expires_at_monotonic).
        # Python dicts preserve insertion order, giving cheap oldest-first
        # eviction without an extra structure.
        self._entries: dict[str, tuple[AuthenticatedUserProtocol, str, float]] = {}

    @property
    def enabled(self) -> bool:
        """Whether caching is active (``ttl_seconds > 0``)."""
        return self._ttl > 0

    def get(self, session_id: str) -> AuthenticatedUserProtocol | None:
        """Return the cached user for ``session_id`` if present and fresh.

        Expired entries are removed on access. Always ``None`` when the
        cache is disabled.

        Args:
            session_id: The session identifier from the signed cookie.

        Returns:
            The cached user, or ``None`` on miss/expiry/disabled.
        """
        if not self.enabled or not session_id:
            return None
        entry = self._entries.get(session_id)
        if entry is None:
            return None
        user, _user_id, expires_at = entry
        if self._now() >= expires_at:
            self._entries.pop(session_id, None)
            return None
        return user

    def put(self, session_id: str, user: AuthenticatedUserProtocol) -> None:
        """Cache ``user`` under ``session_id`` for the configured TTL.

        No-op when disabled, when ``session_id`` is empty, or when the user
        looks like a guest/anonymous record — only successfully
        authenticated users are ever cached.

        Args:
            session_id: The session identifier from the signed cookie.
            user: The fully loaded, active admin user for that session.
        """
        if not self.enabled or not session_id:
            return
        user_id = str(getattr(user, "user_id", "") or "")
        if not user_id or user_id == "guest":
            return
        if session_id not in self._entries and len(self._entries) >= self._max_entries:
            # Evict the oldest entry (insertion order) to stay bounded.
            oldest = next(iter(self._entries))
            self._entries.pop(oldest, None)
        # Re-inserting moves the entry to the newest position.
        self._entries.pop(session_id, None)
        self._entries[session_id] = (user, user_id, self._now() + self._ttl)

    def invalidate(self, session_id: str) -> None:
        """Drop the entry for a single session (logout / remote revoke).

        Args:
            session_id: The session identifier to forget.
        """
        if self._entries.pop(session_id, None) is not None:
            logger.debug("session_cache.invalidated", session_id_prefix=session_id[:8])

    def invalidate_user(self, user_id: str) -> None:
        """Drop every entry belonging to ``user_id`` (bulk revocation).

        Linear scan — the cache is size-bounded (≤ ``max_entries``), so this
        stays trivially cheap.

        Args:
            user_id: The admin user whose sessions must all be forgotten.
        """
        if not user_id:
            return
        stale = [
            sid for sid, (_u, uid, _exp) in self._entries.items() if uid == user_id
        ]
        for sid in stale:
            self._entries.pop(sid, None)
        if stale:
            logger.debug(
                "session_cache.user_invalidated", user_id=user_id, entries=len(stale)
            )

    def clear(self) -> None:
        """Drop all entries."""
        self._entries.clear()

    def __len__(self) -> int:
        """Number of stored entries (including not-yet-reaped expired ones)."""
        return len(self._entries)


__all__ = ["DEFAULT_MAX_ENTRIES", "DEFAULT_TTL_SECONDS", "SessionUserCache"]
