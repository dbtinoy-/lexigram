"""Error handling middleware with detailed error pages."""

from __future__ import annotations

import traceback
from typing import Any

from starlette.exceptions import HTTPException as HTTPError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from lexigram.admin.exceptions import NotFoundError
from lexigram.logging import get_logger
from lexigram.ui import el, render_to_string

logger = get_logger(__name__)


class AdminErrorMiddleware(BaseHTTPMiddleware):
    """HTTP middleware that catches exceptions and displays detailed error pages or JSON responses.

    Uses BaseHTTPMiddleware for proper exception handling in Starlette applications.
    """

    def __init__(
        self, app, debug: bool = True, login_url: str = "/admin/login"
    ) -> None:
        """Initialize error middleware.

        Args:
            app: ASGI application
            debug: Whether to show detailed error pages
            login_url: URL to redirect to for 401 Unauthorized
        """
        super().__init__(app)
        self.debug = debug
        self.login_url = login_url

    async def dispatch(self, request: Request, call_next) -> Any:
        """Dispatch method that wraps request processing and catches exceptions."""
        try:
            return await call_next(request)
        except Exception as exc:  # noqa: BLE001 — last-resort error middleware must catch all
            logger.exception(
                "AdminErrorMiddleware caught exception: %s", type(exc).__name__
            )
            return await self.handle(request, exc)

    def _should_return_json(self, request: Request) -> bool:
        """Determine if JSON response is preferred."""
        accept = request.headers.get("accept", "")
        # Check explicit Accept header
        if "application/json" in accept:
            return True
        # Check path heuristic for API requests
        try:
            from lexigram.admin.settings import get_admin_settings

            api_prefix = get_admin_settings().ADMIN_API_PREFIX.rstrip("/")  # type: ignore[attr-defined]
            if request.url.path.startswith(api_prefix):
                # But if it's HTMX, we might prefer HTML fragments
                return not self._is_htmx(request)
        except (ImportError, AttributeError):
            pass
        return False

    def _is_htmx(self, request: Request) -> bool:
        """Check if request is from HTMX."""
        return request.headers.get("hx-request") == "true"

    async def handle(self, request: Request, exc: Exception) -> Response:
        """Handle exceptions and return a Response object.

        This method is compatible with Starlette's exception_handler signature.
        """
        status_code = 500
        message = "Internal Server Error"

        if isinstance(exc, NotFoundError):
            status_code = 404
            message = str(exc)
        elif isinstance(exc, HTTPError):
            status_code = exc.status_code
            message = exc.detail

        # Decide content type
        if self._should_return_json(request):
            return self._make_json_response(status_code, message)
        if self._is_htmx(request):
            return self._make_htmx_response(request, status_code, message, exc)
        return self._make_html_response(request, status_code, message, exc)

    def _make_json_response(self, status_code: int, message: str) -> Response:
        """Create JSON error response."""
        return JSONResponse(
            status_code=status_code,
            content={"error": {"code": status_code, "message": message}},
        )

    def _make_htmx_response(
        self,
        request: Request,
        status_code: int,
        message: str,
        exc: Exception | None = None,
    ) -> Response:
        """Create HTMX error response with professional styling."""
        # 1. Handle 401 - Return JSON with login_url, no HX-Redirect to avoid redirect loop
        if status_code == 401:
            return JSONResponse(
                status_code=401,
                content={"error": "session_expired", "login_url": self.login_url},
            )

        # 2. Map Status to Metadata
        title = "Error"
        icon = "⚠️"

        if status_code == 403:
            title = "Access Denied"
            icon = "🔒"
        elif status_code == 404:
            title = "Not Found"
            icon = "🔍"
        elif status_code == 500:
            title = "Server Error"
            icon = "💥"

        # 3. Handle Debug Details
        debug_html = ""
        debug_button = ""
        if self.debug and exc:
            tb_text = "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__),
            )
            debug_html = f"""
            <div id="error-details-{id(exc)}" class="hidden mt-4 p-4 bg-gray-900 text-gray-100 rounded-lg text-xs overflow-auto max-h-64 font-mono">
              {tb_text}
            </div>
            """
            debug_button = f"""
            <button onclick="document.getElementById('error-details-{id(exc)}').classList.toggle('hidden')" class="mr-2 text-sm font-medium text-primary-600 hover:text-primary-800 dark:text-primary-400 dark:hover:text-primary-300">
              Show Details
            </button>
            """

        # 4. Create Styled Fragment
        html = f"""
        <div class="admin-error-fragment p-6 my-4 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-red-100 dark:border-red-900/50">
          <div class="flex items-center gap-4">
            <div class="w-12 h-12 bg-red-50 dark:bg-red-900/20 rounded-full flex items-center justify-center text-2xl">
              {icon}
            </div>
            <div>
              <h3 class="text-lg font-bold text-gray-900 dark:text-white">{title} ({status_code})</h3>
              <p class="text-gray-600 dark:text-gray-400">{message}</p>
            </div>
          </div>
          {debug_html}
          <div class="mt-4 flex justify-end">
            {debug_button}
            <button onclick="this.closest('.admin-error-fragment').remove()" class="text-sm font-medium text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
              Dismiss
            </button>
          </div>
        </div>
        """

        response = HTMLResponse(html, status_code=200)  # 200 so HTMX swaps by default

        # 4. Trigger Toast Notifications
        from lexigram.serialization import dumps_str

        response.headers["HX-Trigger"] = dumps_str(
            {"showMessage": {"message": f"{title}: {message}", "type": "error"}},
        )

        return response

    def _make_html_response(
        self,
        request: Request,
        status_code: int,
        message: str,
        exc: Exception,
    ) -> Response:
        """Create HTML error response."""

        # 1. Handle 401 - Redirect to Login
        if status_code == 401:
            from starlette.datastructures import URL

            # Only redirect if not already on login page to avoid loops
            if str(request.url.path).rstrip("/") == str(self.login_url).rstrip("/"):
                # We are on login page but still got 401? Probably bad credentials or logic.
                # Just return the page as is or a clean 401?
                # Usually 401 on login page means "Invalid credentials" which is handled by POST.
                # If GET 401, it's weird. Let's redirect to login nicely?
                pass

            login_url = URL(self.login_url).include_query_params(next=str(request.url))
            return RedirectResponse(url=str(login_url), status_code=302)

        # 2. Handle 500 in Debug Mode - Show Traceback
        if status_code == 500 and self.debug and not isinstance(exc, HTTPError):
            html = self._render_debug_error_html(request, exc)
            return HTMLResponse(html, status_code=500)

        # 3. Handle Other Errors (403, 404, 500 production) - Show Styled Page
        from lexigram.admin.lib.template import render_error_page

        title = "Error"
        icon = "⚠️"

        if status_code == 403:
            title = "Access Denied"
            message = "You don't have permission to access this resource."
            icon = "🔒"
        elif status_code == 404:
            title = "Page Not Found"
            message = "The page you're looking for could not be found."
            icon = "🔍"
        elif status_code == 500:
            title = "Internal Server Error"
            message = "Something went wrong on our end."
            icon = "💥"

        html = render_error_page(
            status_code=status_code,
            title=title,
            message=message,
            icon=icon,
            action_text="Go to Dashboard",
            action_url="/admin/",
        )

        return HTMLResponse(html, status_code=status_code)

    def _render_debug_error_html(self, request: Request, exc: Exception) -> str:
        """Render detailed error page HTML."""
        from lexigram.admin.lib.template import render_template

        exc_type = type(exc).__name__
        exc_message = str(exc)

        # Get traceback
        tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
        tb_html = render_to_string(
            el("div", *[el("div", line, class_="tb-line") for line in tb_lines])
        )
        tb_plain = "".join(tb_lines)  # Plain text for copying

        # Get local variables from the last frame
        tb = exc.__traceback__
        while tb and tb.tb_next:
            tb = tb.tb_next

        local_vars = {}
        if tb:
            for key, value in tb.tb_frame.f_locals.items():
                if not key.startswith("__"):
                    try:
                        val_str = repr(value)[:200]
                    except (
                        RuntimeError,
                        ValueError,
                    ) as e:  # Best-effort error handling in debug page
                        # Best-effort: avoid raising during error page rendering; fall back to placeholder
                        from lexigram.logging import get_logger

                        get_logger(__name__).debug(
                            "Failed to repr local var %s: %s",
                            key,
                            e,
                            exc_info=True,
                        )
                        val_str = "<unable to repr>"
                    local_vars[key] = val_str

        from lexigram.admin.lib.security import mask_sensitive_data

        masked_query = mask_sensitive_data(dict(request.query_params))
        masked_locals = mask_sensitive_data(local_vars)

        # Render using template
        return render_template(
            "debug_error.html",
            exc_type=exc_type,
            exc_message=exc_message,
            traceback=tb_html,
            traceback_plain=tb_plain,
            request_method=request.method,
            request_url=str(request.url),
            request_path=request.url.path,
            request_query=masked_query,
            local_vars=masked_locals,
        )
