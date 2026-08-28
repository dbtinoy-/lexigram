"""Standalone server entry point for the Events Timeline Lab."""

from __future__ import annotations

import asyncio

from timeline_lab.app import create_app


async def serve() -> None:
    from lexigram.web.server.runner import run_server

    application = create_app()
    await application.start()
    try:
        run_server(application)
    finally:
        await application.stop()


def main() -> int:
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        return 130
    return 0


__all__ = ["main", "serve"]
