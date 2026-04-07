"""Middleware for initial setup redirection."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from starlette.responses import RedirectResponse

from lexigram.admin.auth.store.protocols import AdminUserStoreProtocol
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_logger(__name__)


class SetupMiddleware:
    """Redirect to the first-run setup wizard when no admin accounts exist.

    This middleware intercepts every HTTP request to the admin sub-app and
    checks whether at least one admin-panel account has been created.  If the
    ``admin_users`` table is empty it issues a 302 to ``{prefix}/setup`` so
    the operator is guided through initial configuration.

    The middleware is mounted by
    :class:`~lexigram.admin.di.bundle_provider.AdminProvider` during
    :meth:`~lexigram.admin.di.bundle_provider.AdminProvider.mount_to_app`
    and receives a fully-resolved :class:`AdminUserStoreProtocol` instance —
    no duck-typing, no ``hasattr`` guards.

    Paths that are always allowed through (bypass the redirect):
        - ``/setup`` and any path ending in ``/setup``
        - ``/static`` paths (asset serving must never redirect)
    """

    def __init__(
        self,
        app: Callable,
        admin_user_store: AdminUserStoreProtocol,
    ) -> None:
        self.app = app
        self._store = admin_user_store

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable,
        send: Callable,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if (
            path == "/setup"
            or path.endswith("/setup")
            or path == "/login"
            or path == "/login/"
            or path == "/logout"
            or path == "/logout/"
            or path.startswith("/static")
            or "/static/" in path
        ):
            logger.debug("setup_middleware.skip path=%s", path)
            await self.app(scope, receive, send)
            return

        prefix = scope.get("root_path", "")
        try:
            admin_count = await self._store.get_admin_count()
            logger.debug(
                "setup_middleware.check admin_count=%s path=%s", admin_count, path
            )
            if admin_count == 0:
                logger.debug("setup_middleware.redirect_to_setup path=%s", path)
                response = RedirectResponse(url=f"{prefix}/setup")
                await response(scope, receive, send)
                return
        except (
            RuntimeError,
            ValueError,
            AttributeError,
            ConnectionError,
            OSError,
        ) as e:
            logger.warning("setup_middleware.count_failed error=%s degraded", e)
            # Degrade gracefully: let the request through. A transient DB
            # failure does not mean "no users exist" — it means "can't check."
            # AuthMiddleware and SetupController will handle their own errors.
            await self.app(scope, receive, send)
            return

        await self.app(scope, receive, send)
