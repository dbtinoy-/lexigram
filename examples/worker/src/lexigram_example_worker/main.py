"""Worker process entrypoint.

Boots the Lexigram Application, registers the WorkerProvider, and runs
until an OS signal (SIGINT / SIGTERM) is received.

Usage::

    python -m lexigram_example_worker.main

Or via uv::

    uv run python -m lexigram_example_worker.main
"""

from __future__ import annotations

import asyncio

from lexigram.app import Application, run_application
from lexigram.logging import get_logger

from lexigram_example_worker.config import WorkerConfig
from lexigram_example_worker.di.provider import WorkerProvider

logger = get_logger(__name__)


async def _main() -> None:
    """Configure and start the worker application.

    Creates the :class:`~lexigram.app.Application`, attaches the
    :class:`~lexigram_example_worker.di.provider.WorkerProvider`, then
    delegates lifecycle control to :func:`~lexigram.app.run_application`.
    """
    config = WorkerConfig()

    logger.info(
        "worker.starting",
        queue_driver=config.queue_driver,
        concurrency=config.concurrency,
        scheduler_enabled=config.scheduler_enabled,
    )

    app = Application(name="lexigram-example-worker")
    app.add_provider(WorkerProvider(config))

    await run_application(app)


def main() -> None:
    """Synchronous entrypoint used by ``python -m`` and script runners."""
    asyncio.run(_main())


if __name__ == "__main__":
    main()
