"""Application entry point — boots the app and starts the web server."""

from __future__ import annotations

import asyncio

from queueworker.app import create_app


def serve() -> None:
    """Start the web server (blocking)."""
    asyncio.run(_async_serve())


async def _async_serve() -> None:
    app = create_app()
    from lexigram.web.server import run_server_async

    await run_server_async(app)
