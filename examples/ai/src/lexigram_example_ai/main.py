"""AI pipeline example application entrypoint.

Boots the Lexigram Application, registers the AIProvider, and runs a
brief demo showing multi-turn chat and a RAG query.

Usage::

    python -m lexigram_example_ai.main

Or via uv::

    uv run python -m lexigram_example_ai.main
"""

from __future__ import annotations

import asyncio

from lexigram.app import Application, run_application
from lexigram.logging import get_logger

from lexigram_example_ai.config import AIConfig
from lexigram_example_ai.di.provider import AIProvider

logger = get_logger(__name__)


async def _main() -> None:
    """Configure and start the AI pipeline application.

    Creates the :class:`~lexigram.app.Application`, attaches the
    :class:`~lexigram_example_ai.di.provider.AIProvider`, then delegates
    lifecycle control to :func:`~lexigram.app.run_application`.
    """
    config = AIConfig()

    logger.info(
        "ai_example.starting",
        llm_driver=config.llm_driver,
        llm_model=config.llm_model,
        vector_driver=config.vector_driver,
    )

    app = Application(name="lexigram-example-ai")
    app.add_provider(AIProvider(config))

    await run_application(app)


def main() -> None:
    """Synchronous entrypoint used by ``python -m`` and script runners."""
    asyncio.run(_main())


if __name__ == "__main__":
    main()
