"""Entry points for the auth web demo.

Run::

    uv run python -m auth_web            # starts the web server on :8081
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from auth_web.module import AuthWebModule
from lexigram.app import Application
from lexigram.web.server.runner import run_server_async


async def _serve(port: int) -> None:
    async with Application.boot(
        name="auth-web",
        modules=[AuthWebModule.configure(port=port)],
    ) as app:
        from lexigram.web.di.provider import WebProvider

        web = await app.container.resolve(WebProvider)
        await run_server_async(web.starlette, host="127.0.0.1", port=port)


def main() -> int:
    parser = argparse.ArgumentParser(description="Auth web demo")
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("AUTH_WEB_PORT", "8081"))
    )
    args = parser.parse_args()
    asyncio.run(_serve(args.port))
    return 0


if __name__ == "__main__":
    sys.exit(main())
