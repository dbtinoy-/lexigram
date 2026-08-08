"""Workers module for Lexigram."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.infra.tasks.protocols import TaskWorkerProtocol
from lexigram.di.module import DynamicModule, Module, module

if TYPE_CHECKING:
    from lexigram.ai.workers.config import WorkersConfig


@module()
class WorkersModule(Module):
    """Module for AI background workers.

    Registers the :class:`~lexigram.ai.workers.di.provider.WorkersProvider`
    which wires the ingestion, embedding, DLQ, and maintenance workers.

    Usage::

        from lexigram.ai.workers.config import WorkersConfig

        @module(
            imports=[WorkersModule.configure(WorkersConfig(...))]
        )
        class AppModule(Module):
            pass
    """

    @classmethod
    def configure(
        cls,
        config: WorkersConfig | None = None,
        enable_scheduler: bool = True,
    ) -> DynamicModule:
        """Create a WorkersModule with explicit configuration.

        Args:
            config: Optional :class:`~lexigram.ai.workers.config.WorkersConfig`.
            enable_scheduler: Start the background maintenance scheduler that
                handles DLQ retries and worker health checks. Defaults to
                ``True``; set to ``False`` to disable all scheduled tasks (e.g.
                when running in a worker-only process).

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.ai.workers.di.provider import WorkersProvider

        return DynamicModule(
            module=cls,
            providers=[
                WorkersProvider(
                    config=config,
                    enable_scheduler=enable_scheduler,
                )
            ],
            exports=[TaskWorkerProtocol],
        )

    @classmethod
    def stub(cls, config: WorkersConfig | None = None) -> DynamicModule:
        """Create a WorkersModule suitable for unit and integration testing.

        Uses in-memory or no-op worker implementations with minimal side
        effects. The background scheduler is disabled by default to prevent
        timer interference between tests.

        Args:
            config: Optional :class:`~lexigram.ai.workers.config.WorkersConfig`
                override. Uses safe test defaults when ``None``.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.ai.workers.di.provider import WorkersProvider

        return DynamicModule(
            module=cls,
            providers=[WorkersProvider(config=config, enable_scheduler=False)],
            exports=[TaskWorkerProtocol],
        )


__all__ = ["WorkersModule"]
