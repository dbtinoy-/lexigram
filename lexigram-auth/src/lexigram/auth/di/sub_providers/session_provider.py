"""Session provider — registers ``SessionManagerImpl`` in the DI container."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.auth.session.manager import SessionManagerImpl
from lexigram.auth.storage.in_memory_stores import InMemorySessionStore
from lexigram.contracts.ai.session import SessionManagerProtocol
from lexigram.contracts.core import HealthCheckResult, HealthStatus, ProviderPriority
from lexigram.di.provider import Provider
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.auth.storage.session_store import SessionStore
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

logger = get_logger(__name__)


class SessionProvider(Provider):
    """Registers :class:`~lexigram.auth.session.manager.SessionManagerImpl` in the container.

    Reads ``max_sessions_per_user`` from the supplied ``AuthConfig`` so that
    the concurrency limit is driven by application configuration.  When no
    config is given the session manager defaults to unlimited sessions.
    """

    def __init__(self, config: Any = None, **kwargs: Any) -> None:
        """Initialise the session provider.

        Args:
            config: Optional :class:`~lexigram.auth.config.AuthConfig`.  Used
                to read ``max_sessions_per_user`` and select the session store
                backend.  When ``None``, sane defaults are used.
            **kwargs: Ignored extra keyword arguments (forwarded from bundle).
        """
        super().__init__(name="sessions", priority=ProviderPriority.SECURITY)
        self._config = config

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register :class:`SessionManagerImpl` as a singleton.

        Args:
            container: The DI container registrar.
        """
        max_sessions: int | None = None
        session_store: SessionStore = InMemorySessionStore()

        if self._config is not None:
            max_sessions = getattr(self._config, "max_sessions_per_user", None)

        session_manager = SessionManagerImpl(
            session_store=session_store,
            max_sessions_per_user=max_sessions,
        )
        container.singleton(SessionManagerImpl, session_manager)
        container.singleton(SessionManagerProtocol, session_manager, validate=False)
        logger.debug(
            "session_provider.registered",
            max_sessions_per_user=max_sessions
            if max_sessions is not None
            else "unlimited",
        )

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Boot the session provider.

        Args:
            container: The read-only container resolver.
        """
        logger.info("session_provider.started")

    async def shutdown(self) -> None:
        """Shut down the session provider."""
        logger.info("session_provider.shutdown")

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Return the health of the session subsystem.

        Args:
            timeout: Ignored; present for protocol compatibility.

        Returns:
            A healthy :class:`~lexigram.contracts.core.HealthCheckResult`.
        """
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            details={
                "max_sessions_per_user": getattr(
                    self._config, "max_sessions_per_user", None
                )
            },
        )


__all__ = ["SessionProvider"]
