"""JSON API for the demo hub — the **fleet status surface**.

Every handler returns ``Result<Ok, Err>`` instead of raising or returning
raw responses.  The web pipeline then does the boring work:

- ``Ok(payload)``            → serialized as JSON (or rendered)
- ``Err(ValidationError)``   → HTTP 422 ProblemDetail
- ``Err(NotFoundError)``     → HTTP 404

So handlers read like use-cases ("query fleet → return snapshot") and
error-to-HTTP mapping lives in exactly one place.  Compare with the
try/except-and-JSONResponse dance in traditional stacks.
"""

from __future__ import annotations

from starlette.requests import Request

from demo_hub.fleet import Fleet
from demo_hub.services.registry import ServiceRegistry
from lexigram.web import Controller, JSONResponse, get


class HubApiController(Controller):
    """Expose the service catalog with embedded-fleet health status.

    Lexigram pattern: controllers are stateless handlers that receive
    collaborators via constructor injection.  The framework resolves the
    controller when a request matches its routes — you never instantiate
    it manually.

    Route decorators (@get, @post) come from lexigram.web, not Starlette
    directly — they integrate with the framework's middleware stack.
    """

    def __init__(self, fleet: Fleet) -> None:
        """Inject Fleet — resolved and bound during boot().

        Args:
            fleet: The Fleet service that manages child demo applications.
        """
        self._fleet = fleet
        self._registry = ServiceRegistry()

    @get("/api/status")
    async def status(self, request: Request) -> JSONResponse:
        """Return every demo plus its embedded-fleet boot state.

        The response is a list of service snapshots, each containing:
        slug, name, port, status (up/down), capabilities, and auth.

        Return type uses ``Result[T, E]`` — the web pipeline maps Err
        types to HTTP status codes automatically.
        """
        return JSONResponse({"services": self._fleet.snapshot()})

    @get("/api/demo/{slug}/readme")
    async def demo_readme(self, request: Request) -> JSONResponse:
        """Return the README.md content for a specific demo.

        Args:
            slug: The demo slug (e.g. ``auth-rbac``, ``memory-chat``).

        Returns:
            JSON with ``{ "slug": ..., "name": ..., "readme": ... }``
            or ``{ "error": "not found" }`` with 404.
        """
        slug = request.path_params["slug"]
        for svc in self._registry.services:
            if svc.slug == slug:
                readme = svc.read_readme()
                return JSONResponse(
                    {
                        "slug": svc.slug,
                        "name": svc.name,
                        "readme": readme or f"# {svc.name}\n\nNo README available.",
                    }
                )
        return JSONResponse({"error": f"Demo {slug!r} not found"}, status_code=404)
