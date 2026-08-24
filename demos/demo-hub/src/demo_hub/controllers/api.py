"""JSON surface for the hub console."""

from __future__ import annotations

from starlette.requests import Request

from demo_hub.fleet import Fleet
from lexigram.web import Controller, JSONResponse, get


class HubApiController(Controller):
    """Expose the service catalog with embedded-fleet health status."""

    def __init__(self, fleet: Fleet) -> None:
        self._fleet = fleet

    @get("/api/status")
    async def status(self, request: Request) -> JSONResponse:
        """Return every demo plus its embedded-fleet boot state."""
        return JSONResponse({"services": self._fleet.snapshot()})
