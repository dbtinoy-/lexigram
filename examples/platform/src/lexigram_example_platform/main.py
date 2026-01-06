"""Platform application entrypoint.

Boots the Lexigram Application, registers the PlatformProvider, and runs
until an OS signal (SIGINT / SIGTERM) is received.

Usage::

    python -m lexigram_example_platform.main

Or via uv::

    uv run python -m lexigram_example_platform.main
"""

from __future__ import annotations

import asyncio

from lexigram.app import Application, run_application
from lexigram.logging import get_logger

from lexigram_example_platform.config import PlatformConfig
from lexigram_example_platform.di.provider import PlatformProvider

logger = get_logger(__name__)


async def _main() -> None:
    """Configure and start the platform application.

    Creates the :class:`~lexigram.app.Application`, attaches the
    :class:`~lexigram_example_platform.di.provider.PlatformProvider`, then
    delegates lifecycle control to :func:`~lexigram.app.run_application`.
    """
    config = PlatformConfig()

    logger.info(
        "platform.starting",
        event_driver=config.event_driver,
        feature_flags_enabled=config.feature_flags_enabled,
        max_tenants=config.max_tenants_per_instance,
    )

    app = Application(name="lexigram-example-platform")
    app.add_provider(PlatformProvider(config))

    await run_application(app)


def main() -> None:
    """Synchronous entrypoint used by ``python -m`` and script runners."""
    asyncio.run(_main())


if __name__ == "__main__":
    main()
