"""JSON surface for the hub console."""

from __future__ import annotations

from starlette.requests import Request

from demo_hub.services.registry import ServiceRegistry
from lexigram.web import Controller, JSONResponse, get


class HubApiController(Controller):
    """Expose the service catalog with live health status."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self._registry = registry

    @get("/api/status")
    async def status(self, request: Request) -> JSONResponse:
        """Return the health status of every registered demo service."""
        return JSONResponse({"services": await self._registry.statuses()})
