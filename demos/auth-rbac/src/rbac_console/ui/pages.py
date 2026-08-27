"""Server-rendered pages + static assets for the RBAC console.

Demonstrates the *page controller* half of a Lexigram web app: HTML lives
in ``ui/views/``, assets in ``ui/static/``, and this controller serves
them with zero business logic — every dynamic interaction goes through
the JSON API in ``controllers/api.py`` instead.  HTMX/vanilla-JS in the
views calls those endpoints directly.
"""

from __future__ import annotations

from pathlib import Path

from starlette.requests import Request

from lexigram.web import Controller, FileResponse, RedirectResponse, get

UI_ROOT = Path(__file__).resolve().parent
VIEWS_ROOT = UI_ROOT / "views"
STATIC_ROOT = UI_ROOT / "static"


def _view(name: str) -> FileResponse:
    return FileResponse(path=VIEWS_ROOT / name, media_type="text/html")


def _static(name: str, media_type: str) -> FileResponse:
    return FileResponse(path=STATIC_ROOT / name, media_type=media_type)


class PagesController(Controller):
    """Serve the console's HTML/JS/CSS; logic lives in the API controller.

    Lexigram convention: page controllers are stateless — they serve
    files and redirect, nothing more.  All dynamic behavior goes through
    the JSON API (RbacApiController).  HTMX/vanilla-JS in the views
    calls those endpoints directly.

    If you use an external frontend (React, Vue), omit this controller
    entirely — RbacApiController is all you need.
    """

    def __init__(self) -> None:
        """Stateless: no constructor dependencies needed."""

    @get("/")
    async def index(self, request: Request) -> RedirectResponse:
        """Redirect root to /matrix — convention: root serves the main view."""
        return RedirectResponse(url="/matrix", status_code=307)

    @get("/login")
    async def login_page(self, request: Request) -> FileResponse:
        return _view("login.html")

    @get("/matrix")
    async def matrix_page(self, request: Request) -> FileResponse:
        # The JS client calls /api/me and redirects to /login on 401.
        return _view("matrix.html")

    @get("/static/style.css")
    async def stylesheet(self, request: Request) -> FileResponse:
        return _static("style.css", "text/css")

    @get("/static/app.js")
    async def app_js(self, request: Request) -> FileResponse:
        return _static("app.js", "text/javascript")

    @get("/static/matrix.js")
    async def matrix_js(self, request: Request) -> FileResponse:
        return _static("matrix.js", "text/javascript")


__all__ = ["PagesController"]
