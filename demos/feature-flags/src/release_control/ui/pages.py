"""Static page controller for the Release Control Lab."""

from __future__ import annotations

from pathlib import Path

from starlette.requests import Request

from lexigram.web import Controller, FileResponse, get

ROOT = Path(__file__).resolve().parent


class ReleaseControlPageController(Controller):
    """Serve the no-build browser console."""

    @get("/")
    async def console(self, request: Request) -> FileResponse:
        return FileResponse(ROOT / "views/release.html", media_type="text/html")

    @get("/static/style.css")
    async def stylesheet(self, request: Request) -> FileResponse:
        return FileResponse(ROOT / "static/style.css", media_type="text/css")

    @get("/static/app.js")
    async def app_js(self, request: Request) -> FileResponse:
        return FileResponse(ROOT / "static/app.js", media_type="text/javascript")


__all__ = ["ReleaseControlPageController"]
