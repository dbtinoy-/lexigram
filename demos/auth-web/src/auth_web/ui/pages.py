"""Static UI file-serving routes (no logic — assets only)."""

from __future__ import annotations

from pathlib import Path

from starlette.requests import Request

from lexigram.web import Controller, FileResponse, RedirectResponse, get

UI_ROOT = Path(__file__).resolve().parent
VIEWS_ROOT = UI_ROOT / "views"
STATIC_ROOT = UI_ROOT / "static"


def _view(name: str) -> FileResponse:
    """Serve one HTML view."""
    return FileResponse(path=VIEWS_ROOT / name, media_type="text/html")


def _static(name: str, media_type: str) -> FileResponse:
    """Serve one static asset."""
    return FileResponse(path=STATIC_ROOT / name, media_type=media_type)


class PagesController(Controller):
    """Serve the demo's HTML/JS/CSS; all logic lives in the API controller."""

    def __init__(self) -> None:
        """Stateless: every handler reads straight from the ui/ folder."""

    @get("/")
    async def index(self, request: Request) -> RedirectResponse:
        """Send browsers to the login page; the JS client bounces logged-in
        users to /profile via /api/me."""
        return RedirectResponse(url="/login", status_code=307)

    @get("/login")
    async def login_page(self, request: Request) -> FileResponse:
        return _view("login.html")

    @get("/register")
    async def register_page(self, request: Request) -> FileResponse:
        return _view("register.html")

    @get("/profile")
    async def profile_page(self, request: Request) -> FileResponse:
        # The JS client calls /api/me and redirects to /login on 401.
        return _view("profile.html")

    @get("/password")
    async def password_page(self, request: Request) -> FileResponse:
        return _view("password.html")

    @get("/static/style.css")
    async def stylesheet(self, request: Request) -> FileResponse:
        return _static("style.css", "text/css")

    @get("/static/app.js")
    async def app_js(self, request: Request) -> FileResponse:
        return _static("app.js", "text/javascript")

    @get("/static/logo.png")
    async def logo(self, request: Request) -> FileResponse:
        return _static("logo.png", "image/png")

    @get("/static/icon.png")
    async def icon(self, request: Request) -> FileResponse:
        return _static("icon.png", "image/png")


__all__ = ["PagesController"]
