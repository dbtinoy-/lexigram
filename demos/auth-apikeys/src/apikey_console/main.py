"""Entry points for the API-keys console demo.

Run::

    uv run python -m apikey_console            # serves application.yaml (:8091)

Server host/port come from ``application.yaml`` (``web.server``); override
without editing the file via ``LEX_WEB__SERVER__PORT``.
"""

from __future__ import annotations

import asyncio
import sys

from apikey_console.config import bind_web, load_lex_config
from apikey_console.module import ApiKeysModule
from lexigram.app import Application


async def _serve() -> None:
    from lexigram.web.di.provider import WebProvider
    from lexigram.web.server.runner import run_server_async

    web_config = bind_web()
    async with Application.boot(
        name="apikeys-console",
        modules=[ApiKeysModule.configure()],
        config=load_lex_config(),
    ) as app:
        web = await app.container.resolve(WebProvider)
        await run_server_async(
            web.starlette,
            host=web_config.server.host,
            port=web_config.server.port,
        )


def main() -> int:
    asyncio.run(_serve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
