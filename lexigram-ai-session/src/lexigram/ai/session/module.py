"""Session module for dependency injection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.ai.session import SessionManagerProtocol, SessionStoreProtocol
from lexigram.di.module import DynamicModule, Module, module

if TYPE_CHECKING:
    from lexigram.ai.session.config import SessionConfig


@module()
class SessionModule(Module):
    """AI conversation session management integration.

    Call :meth:`configure` to register
    :class:`~lexigram.contracts.ai.session.SessionStoreProtocol` and
    :class:`~lexigram.contracts.ai.session.SessionManagerProtocol`
    implementations for injection.

    Usage::

        from lexigram.ai.session.config import SessionConfig

        @module(
            imports=[
                SessionModule.configure(
                    SessionConfig(backend="cache"),
                    enable_cleanup_scheduler=True,
                )
            ]
        )
        class AppModule(Module):
            pass

    Error Handling::

        Session operations surface typed exceptions that can be caught
        directly or handled via the Result pattern::

            from lexigram.ai.session.exceptions import (
                SessionError,          # base — catch-all
                SessionNotFoundError,  # session ID not in store
                SessionClosedError,    # write on a closed session
                SessionExpiredError,   # TTL exceeded
                CheckpointNotFoundError,# checkpoint ID not found
            )

    Exports:
        :class:`~lexigram.contracts.ai.session.SessionStoreProtocol`,
        :class:`~lexigram.contracts.ai.session.SessionManagerProtocol`,
        :class:`~lexigram.ai.session.exceptions.SessionError`,
        :class:`~lexigram.ai.session.exceptions.SessionNotFoundError`,
        :class:`~lexigram.ai.session.exceptions.SessionClosedError`,
        :class:`~lexigram.ai.session.exceptions.SessionExpiredError`,
        :class:`~lexigram.ai.session.exceptions.CheckpointNotFoundError`
    """

    @classmethod
    def configure(
        cls,
        config: SessionConfig | None = None,
        *,
        enable_cleanup_scheduler: bool = True,
    ) -> DynamicModule:
        """Create a SessionModule with the given configuration.

        Args:
            config: :class:`~lexigram.ai.session.config.SessionConfig`, a
                plain ``dict`` of the same keys, or ``None`` to use defaults.
            enable_cleanup_scheduler: Start the background expired-session
                cleanup loop during boot. Defaults to ``True``.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.ai.session.di.provider import SessionProvider

        return DynamicModule(
            module=cls,
            providers=[
                SessionProvider(
                    config=config,
                    enable_cleanup_scheduler=enable_cleanup_scheduler,
                )
            ],
            exports=[
                SessionStoreProtocol,
                SessionManagerProtocol,
            ],
        )

    @classmethod
    def stub(cls, config: SessionConfig | None = None) -> DynamicModule:
        """Create a SessionModule suitable for unit and integration testing.

        Uses in-memory store with the cleanup scheduler disabled to avoid
        background tasks during tests.

        Args:
            config: Optional config override. Uses safe test defaults when None.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.ai.session.di.provider import SessionProvider

        return DynamicModule(
            module=cls,
            providers=[
                SessionProvider(
                    config=config,
                    enable_cleanup_scheduler=False,
                )
            ],
            exports=[
                SessionStoreProtocol,
                SessionManagerProtocol,
            ],
        )


__all__ = ["SessionModule"]
