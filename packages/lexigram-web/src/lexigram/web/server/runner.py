"""ASGI server execution. Runs the configured web application."""

from __future__ import annotations

from typing import Any

from lexigram.logging import get_logger

logger = get_logger(__name__)


def _to_import_string(app: Any) -> str | None:
    """Derive an import string (``module:attr``) from an ASGI app instance.

    Granian requires a string import path for multiprocessing workers.
    """
    try:
        module = app.__class__.__module__
        if module == "builtins" or module.startswith("starlette."):
            return None
        for candidate in ("app", "application", "asgi"):
            if hasattr(app.__class__, candidate):
                return f"{module}:{candidate}"
        return f"{module}:{app.__class__.__name__}"
    except (AttributeError, TypeError):
        return None


def run_server(
    app: Any,
    host: str | None = None,
    port: int | None = None,
    **kwargs: Any,
) -> None:
    """Run the web application.

    Uses Granian when ``app`` is a string import path (multiprocess-safe).
    Falls back to Uvicorn when ``app`` is an instance (Granian cannot accept
    instances directly).

    Args:
        app: ASGI application instance or import string (``"module:attr"``).
        host: Bind address.  Reads from ``app.config.web.server.host``
            when not provided.
        port: Bind port.  Reads from ``app.config.web.server.port``
            when not provided.
        **kwargs: Additional arguments (passed to Uvicorn config).

    Raises:
        ImportError: If neither Granian nor Uvicorn is installed.
    """
    if host is None or port is None:
        host, port = _resolve_web_config(app, host, port)

    if isinstance(app, str):
        _run_granian(app, host, port, **kwargs)
        return

    _run_uvicorn(app, host, port, **kwargs)


def _resolve_web_config(
    app: Any, host: str | None, port: str | int | None
) -> tuple[str, int]:
    """Read host/port from app.config when not explicitly provided."""
    config = getattr(app, "config", None)
    if config is None:
        return host or "127.0.0.1", int(port or 8000)
    try:
        from lexigram.web.config import WebConfig
        web = config.get_section("web", WebConfig)
        return host or web.server.host, int(port or web.server.port)
    except Exception:
        return host or "127.0.0.1", int(port or 8000)


def _run_granian(
    app: str,
    host: str,
    port: int,
    **kwargs: Any,
) -> None:
    """Run via Granian (multiprocess)."""
    try:
        from granian import Granian
        from granian.constants import Interfaces
    except ImportError as e:
        raise ImportError(
            "Granian is not installed. Install 'granian' to use run_server() with string apps.",
        ) from e

    logger.info("starting_granian_server", host=host, port=port, kwargs=kwargs)
    server = Granian(
        app,
        address=host,
        port=port,
        interface=Interfaces.ASGI,
        **kwargs,
    )
    server.serve()


async def run_server_async(
    app: Any,
    host: str | None = None,
    port: int | None = None,
    **kwargs: Any,
) -> None:
    """Run the web application asynchronously.

    Uses Uvicorn (supports both string paths and app instances). Prefer
    :func:`run_server` for production deployments with Granian.

    Args:
        app: ASGI application instance or import string.
        host: Bind address.  Reads from ``app.config.web.server.host``
            when not provided.
        port: Bind port.  Reads from ``app.config.web.server.port``
            when not provided.
        **kwargs: Additional arguments passed to Uvicorn config.
    """
    import uvicorn

    # Auto-consume from application.yaml when host/port not explicit.
    if host is None or port is None:
        host, port = _resolve_web_config(app, host, port)

    logger.info("starting_uvicorn_server", host=host, port=port, kwargs=kwargs)
    config = uvicorn.Config(app, host=host, port=port, **kwargs)
    server = uvicorn.Server(config)
    await server.serve()


def _run_uvicorn(
    app: Any,
    host: str,
    port: int,
    **kwargs: Any,
) -> None:
    """Run via Uvicorn (supports app instances)."""
    import asyncio

    import uvicorn

    logger.info("starting_uvicorn_server", host=host, port=port, kwargs=kwargs)
    config = uvicorn.Config(app, host=host, port=port, **kwargs)
    server = uvicorn.Server(config)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(server.serve())


__all__ = ["run_server", "run_server_async"]
