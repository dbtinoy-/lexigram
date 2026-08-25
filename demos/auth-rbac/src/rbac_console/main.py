"""Entry points for the RBAC console demo.

Run::

    uv run python -m rbac_console            # serves application.yaml (:8090)

Server host/port come from ``application.yaml`` (``web.server``); override
without editing the file via ``LEX_WEB__SERVER__PORT``.
"""

from __future__ import annotations

import asyncio
import sys

from lexigram.app import Application
from rbac_console.config import bind_web, load_lex_config
from rbac_console.module import RbacModule


async def _serve() -> None:
    from lexigram.web.di.provider import WebProvider
    from lexigram.web.server.runner import run_server_async

    web_config = bind_web()
    async with Application.boot(
        name="rbac-console",
        modules=[RbacModule.configure()],
        config=load_lex_config(),
    ) as app:
        web = await app.container.resolve(WebProvider)
        await run_server_async(
            web.starlette, host=web_config.server.host, port=web_config.server.port
        )


def main() -> int:
    asyncio.run(_serve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
