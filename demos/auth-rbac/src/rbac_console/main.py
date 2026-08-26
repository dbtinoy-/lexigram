"""Entry point for the auth-rbac console.

Run::

    uv run python -m rbac_console            # serves application.yaml

Server host/port come from ``application.yaml`` (``web.server``); override
without editing the file via ``LEX_WEB__SERVER__PORT``.

Lifecycle teaching notes:
- No config object is passed anywhere: ``Application`` loads
  ``application.yaml`` itself, and every provider with a ``config_key``
  receives its typed section automatically before boot.
- ``Application.boot(...)`` is the idiomatic context manager: it creates the
  app, starts every provider in dependency order, yields, and *guarantees*
  ``stop()`` runs on exit — even on exceptions or Ctrl-C.
- Inside the block the app is ``STARTED``: the container is frozen (no new
  registrations) yet fully resolvable — this is where servers run. Resolving
  ``WebProvider`` here demonstrates post-start resolution; its auto-injected
  ``.config`` carries the server host/port.
"""

from __future__ import annotations

import asyncio
import sys

from lexigram.logging import get_logger
from rbac_console.app import build_modules, build_providers
from rbac_console.config import load_lex_config

logger = get_logger(__name__)


async def serve() -> None:
    """Boot once and serve until interrupted; stop cleanly afterwards."""
    from lexigram.web.di.provider import WebProvider
    from lexigram.web.server.runner import run_server_async

    config = load_lex_config()  # cwd-proof: absolute path to this demo's yaml

    async with Application.boot(
        name="rbac-console",
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
