"""Factory functions for creating admin applications."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware

from lexigram.admin.auth.services._cookie_config import build_session_cookie_kwargs
from lexigram.admin.di.bundle_provider import AdminProvider
from lexigram.admin.middleware.correlation import AdminCorrelationMiddleware
from lexigram.admin.settings.loader import AdminConfigLoader
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Sequence

    from lexigram.admin.config import AdminConfig
    from lexigram.admin.resources.base import Resource

logger = get_logger(__name__)


async def create_app(
    *,
    resources: Sequence[type | Resource] | dict[str, type | Resource] | None = None,
    config: AdminConfig | None = None,
    config_path: Path | str | None = None,
    title: str = "Lexigram Admin",
    prefix: str = "/admin",
    debug: bool = False,
    database_url: str | None = None,
    container: Any | None = None,
    **kwargs: Any,
) -> Starlette:
    """Create a complete, ready-to-serve admin ASGI application.

    Runs the full provider lifecycle (``register`` → ``boot`` →
    ``mount_to_app``) so the returned app has the admin panel mounted at
    ``config.prefix`` — the one-call equivalent of wiring
    :class:`AdminProvider` by hand::

        app = await create_app(resources=[ProductResource])
        uvicorn.run(app, host="0.0.0.0", port=8000)

    Args:
        resources: Resource classes/instances (list or ``{name: resource}``).
        config: Fully-built admin configuration; overrides ``config_path``.
        config_path: YAML config file to load when ``config`` is not given.
        title: Panel title used when building a default config.
        prefix: Mount prefix used when building a default config.
        debug: Debug flag for the default config and Starlette app.
        database_url: Database URL for admin persistence (auth, sessions,
            audit). Defaults to ``sqlite+aiosqlite:///admin.db`` when no
            pre-built container is supplied.
        container: Optional pre-populated DI container (e.g. with a database
            and custom stores already registered). When omitted a fresh
            container with a :class:`DatabaseProvider` is created.
        **kwargs: Forwarded to :class:`AdminProvider` (e.g. ``contributors``).

    Returns:
        A Starlette application with the admin panel mounted.
    """
    from lexigram.admin.config import AdminConfig as AdminConfigCls

    if config is None and config_path is not None:
        loader = AdminConfigLoader(yaml_path=Path(config_path))
        config = await loader.load()

    if config is None:
        config = AdminConfigCls(title=title, prefix=prefix, debug=debug)

    resources_list: list[Any] = []
    if resources:
        if isinstance(resources, dict):
            resources_list = list(resources.values())
        else:
            resources_list = list(resources)

    if container is None:
        from lexigram.di.container import Container
        from lexigram.sql.di.provider import DatabaseProvider

        container = Container()
        db_provider = DatabaseProvider(
            config=database_url or "sqlite+aiosqlite:///admin.db"
        )
        await db_provider.register(container)
        await db_provider.boot(container)
    elif database_url is not None:
        from lexigram.sql.di.provider import DatabaseProvider

        db_provider = DatabaseProvider(config=database_url)
        await db_provider.register(container)
        await db_provider.boot(container)

    admin = AdminProvider(config=config, resources=resources_list, **kwargs)
    await admin.register(container)
    await admin.boot(container)

    cookie_kwargs = build_session_cookie_kwargs(config.auth)
    middleware = [
        Middleware(AdminCorrelationMiddleware),
        Middleware(SessionMiddleware, **cookie_kwargs),
    ]

    app = Starlette(
        debug=debug or config.debug,
        middleware=middleware,
    )
    await admin.mount_to_app(app, container)

    logger.info("Admin application created at %s", config.prefix)
    return app


async def create_admin_provider(
    *,
    resources: Sequence[type | Resource] | dict[str, type | Resource] | None = None,
    config: AdminConfig | None = None,
    config_path: Path | str | None = None,
    title: str = "Lexigram Admin",
    prefix: str = "/admin",
    debug: bool = False,
    **kwargs: Any,
) -> AdminProvider:
    """Create an AdminProvider for use with Application."""
    from lexigram.admin.config import AdminConfig as AdminConfigCls

    if config is None and config_path is not None:
        loader = AdminConfigLoader(yaml_path=Path(config_path))
        config = await loader.load()

    if config is None:
        config = AdminConfigCls(title=title, prefix=prefix, debug=debug)

    resources_list: list[Any] = []
    if resources:
        if isinstance(resources, dict):
            resources_list = list(resources.values())
        else:
            resources_list = list(resources)

    admin = AdminProvider(config=config, resources=resources_list)
    logger.info("AdminProvider created for prefix %s", prefix)
    return admin


__all__ = [
    "create_admin_provider",
    "create_app",
]
