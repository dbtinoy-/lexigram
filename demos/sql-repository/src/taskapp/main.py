"""Serve the SQL-backed task repository console."""

from __future__ import annotations

import asyncio
import sys

from taskapp.app import create_app


async def serve() -> None:
    """Boot the database, repository, and standalone web server."""
    from lexigram.web.server.runner import run_server

    app = create_app()
    await app.start()
    try:
        run_server(app)
    finally:
        await app.stop()


def main() -> int:
    """Translate asyncio interrupts into a conventional exit code."""
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())


__all__ = ["main", "serve"]
