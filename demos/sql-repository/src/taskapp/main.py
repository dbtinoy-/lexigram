"""Serve the sql-repository REST API.

Convention followed: **Application boot** — ``create_app()`` builds the
composition root, this file boots it and runs the web server.  Host/port
are read automatically from ``application.yaml`` — no manual config wiring
needed.

Run::

    uv run python -m taskapp

The server exposes:

- ``GET /api/tasks/users``       — list users
- ``POST /api/tasks/users``      — create user
- ``GET /api/tasks/projects``    — list projects
- ``POST /api/tasks/projects``   — create project
- ``GET /api/tasks/tasks``       — list tasks
- ``POST /api/tasks/tasks``      — create task
- ``PUT /api/tasks/tasks/{id}/status`` — update task status
"""

from __future__ import annotations

import asyncio
import sys

from lexigram.logging import get_logger
from taskapp.app import create_app

logger = get_logger(__name__)


async def serve() -> None:
    """Boot and serve until interrupted.

    ``app.start()`` triggers the full lifecycle:
    register → freeze → boot (seeding happens here) → server start.
    The ``finally`` block ensures ``stop()`` runs even on errors.
    """
    from lexigram.web.server.runner import run_server

    app = create_app()
    await app.start()
    try:
        run_server(app)
    finally:
        await app.stop()


def main() -> int:
    """Sync entry point: translate asyncio interrupts into exit codes."""
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())


__all__ = ["main", "serve"]
