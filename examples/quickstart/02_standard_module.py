"""
Standard Module Boot Example
=============================

Demonstrates:
- Boot StandardModule (batteries-included)
- Resolve Invoker from container
- Invoke arbitrary functions with DI

Run: python examples/quickstart/04_standard_module.py
"""

from __future__ import annotations

import asyncio
import sys

from lexigram.app import Application, StandardModule
from lexigram.app.invoker import Invoker
from lexigram.logging import get_logger

logger = get_logger(__name__)


async def my_job() -> None:
    """Example job that gets invoked with DI."""
    logger.info("job_running")


async def main() -> None:
    """Boot a standard Lexigram application and invoke a callable."""
    try:
        async with Application.boot(modules=[StandardModule.configure()]) as app:
            logger.info("app_booted")
            invoker = await app.container.resolve(Invoker)
            await invoker.invoke(my_job)
            logger.info("job_completed")
    except Exception as e:
        logger.error("boot_failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
