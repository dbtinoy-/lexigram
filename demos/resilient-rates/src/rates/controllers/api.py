"""REST surface for the resilient rates demo.

Exposes the rate desk over HTTP so resilience behaviour can be driven live
from a browser or curl while watching retry/breaker/stale reactions:

- ``GET /rates/{pair}``        — fetch a quote (cache → single-flight →
  resilient upstream → stale fallback)
- ``GET /stats``               — hit/miss/upstream/retry/stale counters
- ``POST /scenario/{name}``    — flip the upstream health scenario
  (``healthy | flaky | down | slow``)
- ``POST /cache/clear``        — drop cached quotes

Domain failures map to status codes: unknown pair/scenario → 404.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse

from lexigram.web import Controller, get, post
from rates.provider import FaultController, Scenario
from rates.services.rates_service import RatesService


class RatesApiController(Controller):
    """Expose the rate desk and its fault controls over HTTP."""

    def __init__(self, service: RatesService, faults: FaultController) -> None:
        self.service = service
        self.faults = faults

    @get("/rates/{pair:path}")
    async def fetch_rate(self, request: Request) -> JSONResponse:
        """Fetch one quote through the full resilience pipeline."""
        pair = request.path_params["pair"].upper().strip("/")
        if "/" not in pair:
            return JSONResponse(
                {"error": f"invalid pair {pair!r}; expected BASE/QUOTE"},
                status_code=404,
            )
        result = await self.service.fetch(pair)
        if result.is_err():
            return JSONResponse({"error": str(result.unwrap_err())}, status_code=503)
        quote = result.unwrap()
        payload = asdict(quote)
        payload["rate"] = str(quote.rate)
        return JSONResponse(payload)

    @get("/stats")
    async def stats(self, request: Request | None = None) -> dict[str, Any]:
        """Return the aggregate service counters."""
        return asdict(self.service.stats())

    @post("/cache/clear")
    async def clear_cache(self, request: Request | None = None) -> dict[str, Any]:
        """Drop all cached quotes."""
        await self.service.clear_cache()
        return {"ok": True}

    @post("/scenario/{name}")
    async def set_scenario(self, request: Request) -> JSONResponse:
        """Flip the simulated upstream health scenario."""
        raw = request.path_params["name"]
        try:
            scenario = Scenario(raw)
        except ValueError:
            valid = ", ".join(s.value for s in Scenario)
            return JSONResponse(
                {"error": f"unknown scenario {raw!r}; valid: {valid}"},
                status_code=404,
            )
        self.faults.set(scenario)
        return JSONResponse({"ok": True, "scenario": scenario.value})


__all__ = ["RatesApiController"]
