from __future__ import annotations

from typing import TYPE_CHECKING, Any

from starlette.responses import JSONResponse

from lexigram.admin.openapi.resource_converter import resources_to_openapi_spec

if TYPE_CHECKING:
    from starlette.requests import Request


class OpenAPIController:
    """Serves the OpenAPI specification for admin resources.

    Mounted at ``/admin/openapi.json`` (or the configured admin prefix).
    """

    def __init__(self, resources: dict[str, Any]) -> None:
        self._resources = resources

    async def get_spec(self, request: Request) -> JSONResponse:
        """Handle ``GET /admin/openapi.json``.

        Returns:
            A JSON response containing the full OpenAPI 3.0.3 spec.
        """
        spec = resources_to_openapi_spec(self._resources)
        return JSONResponse(spec)


__all__ = ["OpenAPIController"]
