"""Entry points for the RBAC console demo.

Run::

    uv run python -m rbac_console            # starts the web server on :8090
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from lexigram.app import Application
from lexigram.web.server.runner import run_server_async
from rbac_console.module import RbacModule


async def _serve(port: int) -> None:
    async with Application.boot(
        name="rbac-console",
        modules=[RbacModule.configure(port=port)],
    ) as app:
        from lexigram.web.di.provider import WebProvider

        web = await app.container.resolve(WebProvider)
        await run_server_async(web.starlette, host="127.0.0.1", port=port)


def main() -> int:
    parser = argparse.ArgumentParser(description="RBAC console demo")
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("RBAC_PORT", "8090"))
    )
    args = parser.parse_args()
    asyncio.run(_serve(args.port))
    return 0


if __name__ == "__main__":
    sys.exit(main())
