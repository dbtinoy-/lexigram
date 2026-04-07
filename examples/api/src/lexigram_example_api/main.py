"""Application entry-point.

Bootstraps the Lexigram Application, adds all providers via
:class:`~lexigram_example_api.module.AppModule`, and starts the ASGI server.

Usage::

    # From the workspace root:
    uv run python -m lexigram_example_api.main

    # With custom settings via environment variables:
    APP_PORT=9000 APP_DEBUG=true uv run python -m lexigram_example_api.main

The application can also be used as a raw ASGI app (e.g. with Gunicorn)::

    # gunicorn -w 4 -k uvicorn.workers.UvicornWorker \
    #   "lexigram_example_api.main:create_app()"
"""

from __future__ import annotations

import asyncio

from lexigram import Application
from lexigram.logging import get_logger

from lexigram_example_api.config import AppConfig
from lexigram_example_api.module import AppModule

logger = get_logger(__name__)


def create_app() -> Application:
    """Create and return a configured :class:`~lexigram.app.base.Application`.

    Suitable for use as an ASGI callable in Gunicorn / Uvicorn deployments::

        uvicorn lexigram_example_api.main:create_app --factory

    Returns:
        A fully configured ``Application`` instance (not yet started).
    """
    cfg = AppConfig()
    app = Application(name=cfg.app_name)
    app.add_providers(AppModule.build_providers(cfg))
    return app


async def _run() -> None:
    """Start the application and serve HTTP traffic.

    Starts the ASGI application, then uses Uvicorn (if available) or falls
    back to a simple lifecycle smoke-test for environments without Uvicorn.
    """
    cfg = AppConfig()
    app = create_app()

    await app.start()
    logger.info(
        "server_starting",
        host=cfg.host,
        port=cfg.port,
        debug=cfg.debug,
    )

    try:
        import uvicorn  # type: ignore[import-untyped]

        config = uvicorn.Config(
            app=app,
            host=cfg.host,
            port=cfg.port,
            log_level="debug" if cfg.debug else "info",
            loop="asyncio",
        )
        server = uvicorn.Server(config)
        await server.serve()
    except ImportError:
        logger.warning(
            "uvicorn_not_installed",
            hint="Install with: uv add uvicorn[standard]",
        )
        # Keep the application running so providers can be exercised in tests
        try:
            await asyncio.sleep(float("inf"))
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass
    finally:
        await app.stop()
        logger.info("server_stopped")


if __name__ == "__main__":
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        logger.info("shutdown_requested_by_user")
