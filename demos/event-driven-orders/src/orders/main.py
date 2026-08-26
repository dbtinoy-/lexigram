"""Entry point for the event-driven orders REST API.

Run::

    uv run python -m orders serve

Host/port come from ``application.yaml`` (``web.server``); override without
editing the file via ``LEX_WEB__SERVER__PORT``. Teaching commands
(place/pay/ship/list/outbox/demo) live in ``orders.cli``.

Lifecycle teaching notes:
- ``Application.boot(...)`` is the idiomatic context manager: it creates the
  app, starts every provider in dependency order, yields, and *guarantees*
  ``stop()`` runs on exit — even on exceptions or Ctrl-C.
- Inside the block the app is ``STARTED``: the container is frozen (no new
  registrations) yet fully resolvable — this is where servers run. The CQRS
  wiring is already done too: ``OrdersProvider.boot`` resolved ``OrdersApi``
  during start, registering every command handler and event subscription
  before the first request arrives.
- Resolving ``WebProvider`` here demonstrates post-start resolution; its
  auto-injected ``.config`` carries the server host/port.
"""

from __future__ import annotations

import asyncio
import sys

from lexigram.logging import get_logger
from orders.app import build_modules, build_providers
from orders.config import load_lex_config

logger = get_logger(__name__)


async def serve() -> None:
    """Boot once and serve until interrupted; stop cleanly afterwards."""
    from lexigram.app.base import Application
    from lexigram.web.di.provider import WebProvider
    from lexigram.web.server.runner import run_server_async

    config = load_lex_config()  # cwd-proof: absolute path to this demo's yaml

    async with Application.boot(
        name="event-driven-orders",
        config=config,
        modules=build_modules(config),
        providers=build_providers(),
    ) as app:
        web = await app.container.resolve(WebProvider)
        server = web.config.server
        logger.info("server.listening", host=server.host, port=server.port)
        await run_server_async(web.starlette, host=server.host, port=server.port)


def main() -> int:
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
