"""Server-rendered pages + static assets for the memory-chat demo.

Demonstrates the *page controller* half of a Lexigram web app: HTML lives
in ``ui/views/``, assets in ``ui/static/``, and this controller serves
them with zero business logic — every dynamic interaction goes through
the JSON API in ``controllers/api.py`` instead.  HTMX/vanilla-JS in the
views calls those endpoints directly.
"""

from __future__ import annotations

from pathlib import Path

from starlette.requests import Request

from lexigram.web import Controller, FileResponse, get

UI_ROOT = Path(__file__).resolve().parent
VIEWS_ROOT = UI_ROOT / "views"
STATIC_ROOT = UI_ROOT / "static"


def _view(name: str) -> FileResponse:
    """Serve one HTML view."""
    return FileResponse(path=VIEWS_ROOT / name, media_type="text/html")


def _static(name: str, media_type: str) -> FileResponse:
    """Serve one static asset."""
    return FileResponse(path=STATIC_ROOT / name, media_type=media_type)


class ChatPageController(Controller):
    """Serve the console's HTML/JS/CSS; logic lives in the API controller.

    Lexigram convention: page controllers are stateless — they serve
    files and redirect, nothing more.  All dynamic behavior goes through
    the JSON API (ConciergeApiController).  HTMX/vanilla-JS in the views
    calls those endpoints directly.

    If you use an external frontend (React, Vue), omit this controller
    entirely — ConciergeApiController is all you need.
    """

    def __init__(self) -> None:
        """Stateless: no constructor dependencies needed."""

    @get("/")
    async def chat(self, request: Request) -> FileResponse:
        """The single-page console."""
        return _view("chat.html")

    @get("/static/style.css")
    async def stylesheet(self, request: Request) -> FileResponse:
        return _static("style.css", "text/css")

    @get("/static/app.js")
    async def app_js(self, request: Request) -> FileResponse:
        return _static("app.js", "text/javascript")

    @get("/static/logo.png")
    async def logo(self, request: Request) -> FileResponse:
        return _static("logo.png", "image/png")


__all__ = ["ChatPageController"]
