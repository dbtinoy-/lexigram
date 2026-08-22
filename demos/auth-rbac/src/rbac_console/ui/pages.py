"""Static UI file-serving routes for the RBAC console (assets only)."""

from __future__ import annotations

from pathlib import Path

from starlette.requests import Request
from starlette.responses import RedirectResponse

from lexigram.web import Controller, FileResponse, get

UI_ROOT = Path(__file__).resolve().parent
VIEWS_ROOT = UI_ROOT / "views"
STATIC_ROOT = UI_ROOT / "static"


def _view(name: str) -> FileResponse:
    return FileResponse(path=VIEWS_ROOT / name, media_type="text/html")


def _static(name: str, media_type: str) -> FileResponse:
    return FileResponse(path=STATIC_ROOT / name, media_type=media_type)


class PagesController(Controller):
    """Serve the console's HTML/JS/CSS; logic lives in the API controller."""

    def __init__(self) -> None:
        """Stateless: every handler reads straight from the ui/ folder."""

    @get("/")
    async def index(self, request: Request) -> RedirectResponse:
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
