"""Standalone server entry point for Release Control Lab."""

from __future__ import annotations

import asyncio

from release_control.app import create_app


async def serve() -> None:
    """Start the release control server and block until shutdown."""
    from lexigram.web.server.runner import run_server

    app = create_app()
    await app.start()
    try:
        run_server(app)
    finally:
        await app.stop()


def main() -> int:
    """Entry point that runs the async server with graceful Ctrl-C handling."""
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        return 130
    return 0


__all__ = ["main", "serve"]
