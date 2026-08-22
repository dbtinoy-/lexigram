"""Entry points for the API-keys console demo.

Run::

    uv run python -m apikey_console            # starts the web server on :8091
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from apikey_console.module import ApiKeysModule
from lexigram.app import Application
from lexigram.web.server.runner import run_server_async


async def _serve(port: int) -> None:
    async with Application.boot(
        name="apikeys-console",
        modules=[ApiKeysModule.configure(port=port)],
    ) as app:
        from lexigram.web.di.provider import WebProvider

        web = await app.container.resolve(WebProvider)
        await run_server_async(web.starlette, host="127.0.0.1", port=port)


def main() -> int:
    parser = argparse.ArgumentParser(description="API-keys console demo")
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("APIKEYS_PORT", "8091"))
    )
    args = parser.parse_args()
    asyncio.run(_serve(args.port))
    return 0


if __name__ == "__main__":
    sys.exit(main())
