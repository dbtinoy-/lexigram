"""Static UI file-serving routes for the MFA console (assets only)."""

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
    """Serve the console's HTML/JS/CSS; logic lives in the API controller."""

    def __init__(self) -> None:
        """Stateless: every handler reads straight from the ui/ folder."""

    @get("/")
    async def index(self, request: Request) -> RedirectResponse:
        return RedirectResponse(url="/login", status_code=307)

    @get("/login")
    async def login_page(self, request: Request) -> FileResponse:
        return _view("login.html")

    @get("/challenge")
    async def challenge_page(self, request: Request) -> FileResponse:
        return _view("challenge.html")

    @get("/profile")
    async def profile_page(self, request: Request) -> FileResponse:
        return _view("profile.html")

    @get("/static/style.css")
    async def stylesheet(self, request: Request) -> FileResponse:
        return _static("style.css", "text/css")

    @get("/static/app.js")
    async def app_js(self, request: Request) -> FileResponse:
        return _static("app.js", "text/javascript")

    @get("/static/mfa.js")
    async def mfa_js(self, request: Request) -> FileResponse:
        return _static("mfa.js", "text/javascript")



    @get("/static/logo.png")
    async def logo(self, request: Request) -> FileResponse:
        return _static("logo.png", "image/png")

    @get("/static/icon.png")
    async def icon(self, request: Request) -> FileResponse:
        return _static("icon.png", "image/png")

__all__ = ["PagesController"]
