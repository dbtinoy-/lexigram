"""Standalone server entry point for Artifact Vault."""

from __future__ import annotations

import asyncio

from artifact_vault.app import create_app


async def serve() -> None:
    from lexigram.web.server.runner import run_server

    app = create_app()
    await app.start()
    try:
        run_server(app)
    finally:
        await app.stop()


def main() -> int:
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        return 130
    return 0


__all__ = ["main", "serve"]
