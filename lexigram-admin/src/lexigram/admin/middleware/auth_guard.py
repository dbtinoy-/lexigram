"""Session-based auth guard middleware for the Lexigram Admin panel.

Redirects unauthenticated requests to the login page.  Bypass paths
(login, setup, static assets, health) are always passed through so
authentication pages remain accessible before a session exists.
"""

from __future__ import annotations

from urllib.parse import quote

from starlette.responses import RedirectResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

from lexigram.logging import get_logger

logger = get_logger(__name__)

# Paths (or path suffixes) that are always accessible without a session.
_BYPASS_SUFFIXES: frozenset[str] = frozenset(
    {
        "/login",
        "/login/",
        "/logout",
        "/logout/",
        "/setup",
        "/setup/",
        "/health",
        "/health/",
        "/login/2fa",
        "/login/2fa/",
        "/verify-email",
        "/verify-email/",
        "/password-reset",
        "/password-reset/",
        "/register",
        "/register/",
    }
)

_BYPASS_PREFIXES: tuple[str, ...] = (
    "/static/",
    "/admin/static/",
)

# Token-bearing sub-paths that must remain reachable without a session
# (e.g. the email verification and password-reset links emailed to admins).
_BYPASS_TOKEN_PREFIXES: tuple[str, ...] = (
    "/admin/verify-email/",
    "/admin/password-reset/",
)


class AdminAuthGuardMiddleware:
    """Pure ASGI middleware that enforces session-based authentication.

    Any request whose path is not in the bypass list must carry a
    Starlette session with ``admin_user_id`` set.  If the session is
    missing or empty the client is redirected to ``/admin/login``.

    This middleware is intentionally lightweight — it does not touch the
    database.  It relies solely on the signed session cookie that
    ``AuthController`` writes on successful login.
    """

    def __init__(self, app: ASGIApp) -> None:
        """Initialise the middleware.

        Args:
            app: The next ASGI application in the stack.
        """
        self._app = app

    # ------------------------------------------------------------------
    # ASGI callable
    # ------------------------------------------------------------------

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process an incoming HTTP request.

        Args:
            scope: ASGI connection scope.
            receive: ASGI receive callable.
            send: ASGI send callable.
        """
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        path: str = scope.get("path", "")

        if self._is_bypass_path(path):
            await self._app(scope, receive, send)
            return

        # Inspect the Starlette session (populated by SessionMiddleware).
        if "session" in scope:
            user_id = scope["session"].get("admin_user_id")
            if user_id:
                await self._app(scope, receive, send)
                return

        # No valid session — redirect to login preserving the original URL.
        # HTMX requests get HX-Redirect so the browser performs a full page
        # navigation; a plain 307 would make htmx swap the login page into
        # the current component (e.g. a widget container).
        logger.debug("auth_guard.unauthenticated path=%s", path)
        next_url = quote(path, safe="/")
        login_url = f"/admin/login?next={next_url}"
        if self._is_htmx(scope):
            response = Response(status_code=200)
            response.headers["HX-Redirect"] = login_url
        else:
            response = RedirectResponse(url=login_url, status_code=307)
        await response(scope, receive, send)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_htmx(scope: Scope) -> bool:
        """Return True when the request carries the htmx HX-Request header.

        Args:
            scope: ASGI connection scope.

        Returns:
            True for htmx fragment requests.
        """
        headers = dict(scope.get("headers") or ())
        return headers.get(b"hx-request") == b"true"

    def _is_bypass_path(self, path: str) -> bool:
        """Return True if the path should bypass auth enforcement.

        Args:
            path: The request path.

        Returns:
            True when the path maps to a public endpoint or static asset.
        """
        for suffix in _BYPASS_SUFFIXES:
            if path == suffix or path.endswith(suffix):
                return True

        if any(path.startswith(prefix) for prefix in _BYPASS_TOKEN_PREFIXES):
            return True

        return any(path.startswith(prefix) for prefix in _BYPASS_PREFIXES)
