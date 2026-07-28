"""Session cleanup scheduler — background task for expiring old sessions."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from lexigram.ai.session.config import SessionConfig
from lexigram.contracts.ai.session import SessionManagerProtocol
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class SessionCleanupScheduler:
    """Runs a background loop to close sessions that have exceeded their TTL.

    Session TTL allows the system to automatically close abandoned or
    stale sessions, which in turn triggers memory consolidation and
    frees up active session counts for users.

    Args:
        manager: Session manager instance to list and close sessions.
        config: Session configuration containing TTL settings.
    """

    def __init__(
        self,
        manager: SessionManagerProtocol,
        config: SessionConfig,
    ) -> None:
        """Initialise the cleanup scheduler.

        Args:
            manager: The configured session manager instance.
            config: Session configuration.
        """
        self._manager = manager
        self._config = config
        self._running = False
        self._task: asyncio.Task[Any] | None = None

    async def start(self) -> None:
        """Start the background cleanup loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._cleanup_loop())
        logger.info(
            "session_cleanup_started",
            interval=self._config.cleanup_interval_s,
            ttl=self._config.session_ttl,
        )

    async def stop(self) -> None:
        """Stop the background cleanup loop gracefully."""
        if not self._running:
            return
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            logger.info("session_cleanup_stopped")

    async def run_cleanup_pass(self) -> int:
        """Run a single cleanup pass to find and close expired sessions.

        Returns:
            Number of sessions closed during this pass.
        """
        # Session TTL is disabled if set to 0
        if self._config.session_ttl <= 0:
            return 0

        closed_count = 0
        now = datetime.now(UTC)

        # In a real distributed system, we would query the store directly
        # for expired sessions. For the protocol, we list users/sessions.
        # Since this is an abstract implementation, we rely on the store's
        # underlying querying capability if exposed, otherwise we only clean up
        # sessions we actively know about. If working with bounded stores,
        # we iterate.
        try:
            # Assume store is injected into manager and accessible via private getattr
            # or the manager implements an undocumented list_all_active()
            active_sessions = []
            store = getattr(self._manager, "_store", None)
            if store and hasattr(store, "list_all_active"):
                active_sessions = await store.list_all_active()

            for session in active_sessions:
                age_s = (now - session.updated_at).total_seconds()
                if age_s > self._config.session_ttl:
                    try:
                        await self._manager.close(session.session_id)
                        closed_count += 1
                        logger.debug(
                            "session_ttl_expired", session_id=session.session_id
                        )
                    except Exception as e:  # noqa: BLE001  # per-session cleanup must not stop other sessions from being cleaned
                        logger.warning(
                            "session_cleanup_failed",
                            session_id=session.session_id,
                            error=str(e),
                        )
        except Exception as e:  # noqa: BLE001  # cleanup pass error boundary; logged and swallowed
            logger.error("session_cleanup_pass_error", error=str(e))

        if closed_count > 0:
            logger.info("session_cleanup_pass_completed", closed=closed_count)

        return closed_count

    async def _cleanup_loop(self) -> None:
        """Background loop continuously running cleanup passes."""
        while self._running:
            try:
                await asyncio.sleep(self._config.cleanup_interval_s)
                if not self._running:
                    break
                await self.run_cleanup_pass()
            except asyncio.CancelledError:
                break
            except Exception as e:  # noqa: BLE001
                logger.error("session_cleanup_loop_error", error=str(e))
                # Prevent tight loop on persistent error
                await asyncio.sleep(60.0)


__all__ = ["SessionCleanupScheduler"]
