"""Playground page — static serving only (logic lives in the API controller).

Lexigram separates concerns: pages.py serves HTML/CSS/JS,
api.py handles business logic.  This controller is stateless — no
dependencies injected.  In a real app with a SPA frontend, you might
delete this controller entirely and serve static files via WebModule
or an external CDN.
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


class PlaygroundPageController(Controller):
    """Serve the guardrails playground; every handler reads from ui/.

    FileResponse is a Lexigram web primitive for serving
    static files.  The ui/ directory structure (views/, static/) is
    a convention — not enforced by the framework.  Put your HTML
    templates in views/ and assets in static/.
    """

    def __init__(self) -> None:
        """Stateless — no dependencies to inject."""

    @get("/")
    async def playground(self, request: Request) -> FileResponse:
        """The single-page console."""
        return _view("playground.html")

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


__all__ = ["PlaygroundPageController"]
