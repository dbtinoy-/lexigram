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
    **kwargs: Any,
) -> Starlette:
    """Create a complete admin ASGI application."""
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

    AdminProvider(config=config, resources=resources_list)

    cookie_kwargs = build_session_cookie_kwargs(config.auth)
    middleware = [
        Middleware(AdminCorrelationMiddleware),
        Middleware(SessionMiddleware, **cookie_kwargs),
    ]

    app = Starlette(
        debug=debug,
        middleware=middleware,
    )

    logger.info("Admin application created at %s", prefix)
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
