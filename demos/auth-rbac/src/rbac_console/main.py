"""Entry point for the auth-rbac console — the lifecycle lesson.

Run::

    uv run python -m rbac_console            # serves application.yaml

Server host/port come from ``application.yaml`` (``web.server``); override
without editing the file via ``LEX_WEB__SERVER__PORT``.

What this file teaches
----------------------
1. **The boot context manager.**  :meth:`Application.boot` is the idiomatic
   way to run a Lexigram app.  It chains the full state machine —

       CREATED → STARTING → STARTED → (your code runs here) → STOPPING → STOPPED

   — and *guarantees* ``stop()`` executes when the block exits, whether by
   normal return, exception, or Ctrl-C (``KeyboardInterrupt`` maps to exit
   code 130 below).  No try/finally boilerplate, no leaked connections.

2. **Post-start resolution.**  Inside the block the container is frozen
   (no new registrations) but fully resolvable: every provider has run
   ``register()`` and received its typed config section via auto-injection.
   ``app.container.resolve(WebProvider)`` demonstrates exactly that.

3. **Server knobs live in config, not code.**  The resolved provider's
   auto-injected ``.config.server`` carries host/port from YAML (+ env
   overrides), so deployment changes never touch this file.
"""

from __future__ import annotations

import asyncio
import sys

from lexigram.app.base import Application
from lexigram.logging import get_logger
from rbac_console.app import build_modules, build_providers

logger = get_logger(__name__)


async def serve() -> None:
    """Boot once and serve until interrupted; stop cleanly afterwards.

    ``Application.boot(...)`` discovers ``./application.yaml`` itself, so no
    configuration object is passed here.  Resolving ``WebProvider`` after
    start shows the post-start container: everything registered by modules
    and providers is available for the server wiring.
    """
    from lexigram.web.di.provider import WebProvider
    from lexigram.web.server.runner import run_server_async

    async with Application.boot(
        name="rbac-console",
        modules=build_modules(),
        providers=build_providers(),
    ) as app:
        web = await app.container.resolve(WebProvider)
        server = web.config.server
        logger.info("server.listening", host=server.host, port=server.port)
        # Blocks until SIGINT/SIGTERM; uvicorn handles the signals and the
        # boot context manager then stops providers in reverse order.
        await run_server_async(web.starlette, host=server.host, port=server.port)


def main() -> int:
    """Sync wrapper: translate interrupts into a shell-friendly exit code."""
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        return 130  # conventional: terminated by SIGINT
    return 0


if __name__ == "__main__":
    sys.exit(main())
