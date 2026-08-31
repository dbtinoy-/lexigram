"""Error handler controller for Lexigram Admin.

Provides user-friendly error pages for common HTTP errors.
"""

from __future__ import annotations

from urllib.parse import quote_plus

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from lexigram.admin.controllers.base import AdminController
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.lib.template import render_error_page
from lexigram.contracts.web import get
from lexigram.di.decorators import inject


@inject
class ErrorController(AdminController):
    """Error page controller.

    Provides styled error pages for:
    - 401 Unauthorized - Redirects to login
    - 403 Forbidden - Access denied
    - 404 Not Found - Page not found
    - 500 Internal Server Error - Server error
    """

    prefix = "/admin/error"

    def __init__(self, renderer: AdminRenderer):
        super().__init__(renderer)

    def _render_error_page(
        self,
        status_code: int,
        title: str,
        message: str,
        icon: str,
        action_text: str = "Go to Dashboard",
        action_url: str = "/admin/",
        base_url: str = "/admin",
    ) -> HTMLResponse:
        """Render a styled error page using templates.

        Args:
            status_code: HTTP status code
            title: Error title
            message: Error message
            icon: Emoji icon
            action_text: Button text
            action_url: Button URL

        Returns:
            HTMLResponse with styled error page
        """
        html = render_error_page(
            status_code=status_code,
            title=title,
            message=message,
            icon=icon,
            action_text=action_text,
            action_url=action_url,
            base_url=base_url,
        )
        return HTMLResponse(content=html, status_code=status_code)

    @get("/401")
    async def error_401(self, request: Request) -> RedirectResponse:
        """Handle 401 Unauthorized - redirect to login."""
        # Get the original URL for redirect after login.  Error pages are
        # also mounted under custom admin prefixes, so both links must use
        # the request's configured mount.
        admin_home = self._admin_path(request)
        next_url = request.query_params.get("next", admin_home)
        if not (
            next_url.startswith("/")
            and not next_url.startswith("//")
            and not next_url.startswith("/\\")
        ):
            next_url = admin_home
        return RedirectResponse(
            url=f"{self._admin_path(request, '/admin/login')}?next={quote_plus(next_url)}",
            status_code=302,
        )

    @get("/403")
    async def error_403(self, request: Request) -> HTMLResponse:
        """Handle 403 Forbidden."""
        return self._render_error_page(
            status_code=403,
            title="Access Denied",
            message="You don't have permission to access this resource. Please contact your administrator if you believe this is an error.",
            icon="🔒",
            action_url=self._admin_path(request),
            base_url=self._admin_path(request).rstrip("/"),
        )

    @get("/404")
    async def error_404(self, request: Request) -> HTMLResponse:
        """Handle 404 Not Found."""
        return self._render_error_page(
            status_code=404,
            title="Page Not Found",
            message="The page you're looking for doesn't exist. It may have been moved or deleted.",
            icon="🔍",
            action_url=self._admin_path(request),
            base_url=self._admin_path(request).rstrip("/"),
        )

    @get("/500")
    async def error_500(self, request: Request) -> HTMLResponse:
        """Handle 500 Internal Server Error."""
        return self._render_error_page(
            status_code=500,
            title="Internal Server Error",
            message="Something went wrong on our end. Our team has been notified and we're working to fix it.",
            icon="⚠️",
            action_url=self._admin_path(request),
            base_url=self._admin_path(request).rstrip("/"),
        )
