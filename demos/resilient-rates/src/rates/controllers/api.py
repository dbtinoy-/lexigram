"""REST surface for the resilient rates demo.

Exposes the rate desk over HTTP so resilience behaviour can be driven live
from a browser or curl while watching retry/breaker/stale reactions:

- ``GET /rates/{pair}``        — fetch a quote (cache → single-flight →
  resilient upstream → stale fallback)
- ``GET /stats``               — hit/miss/upstream/retry/stale counters
- ``POST /scenario/{name}``    — flip the upstream health scenario
  (``healthy | flaky | down | slow``)
- ``POST /cache/clear``        — drop cached quotes

Errors: handlers return domain ``Result`` values and the framework's result
bridge serializes them — ``RateUnavailableError`` is registered below as an
upstream fault (503). Unknown pair/scenario paths answer with RFC-9457
problem details (404).
"""

from __future__ import annotations

from dataclasses import asdict

from starlette.requests import Request

from lexigram.web import Controller, JSONResponse, get, post
from lexigram.web.errors.problem_detail import ProblemDetail
from lexigram.web.routing.result_bridge import ResultResponseMapper
from rates.exceptions import RateUnavailableError
from rates.repository.simulated_upstream import FaultController, Scenario
from rates.services.rates_service import RatesService

# Domain failure → HTTP: no quote obtainable is an upstream fault (503).
ResultResponseMapper.register(RateUnavailableError, 503)


def _problem(status: int, detail: str) -> JSONResponse:
    """RFC-9457 style problem response."""
    body = ProblemDetail(
        title="Request rejected", status=status, detail=detail
    ).to_dict()
    return JSONResponse(body, status_code=status)


class RatesApiController(Controller):
    """Expose the rate desk and its fault controls over HTTP."""

    def __init__(self, service: RatesService, faults: FaultController) -> None:
        self.service = service
        self.faults = faults

    @get("/rates/{pair:path}")
    async def fetch_rate(self, request: Request) -> JSONResponse:
        """Fetch one quote through the full resilience pipeline.

        A terminal :class:`RateUnavailableError` maps to 503 through the
        framework's result-bridge registry (registered below).
        """
        pair = str(request.path_params["pair"]).upper().strip("/")
        if "/" not in pair:
            return _problem(404, f"invalid pair {pair!r}; expected BASE/QUOTE")
        result = await self.service.fetch(pair)
        if result.is_err():
            return ResultResponseMapper.error_to_response(result.unwrap_err())
        quote = result.unwrap()
        payload = {**quote.to_payload()}
        return JSONResponse(payload)

    @get("/stats")
    async def stats(self, request: Request) -> dict[str, int]:
        """Return the aggregate service counters."""
        return asdict(self.service.stats())

    @post("/cache/clear")
    async def clear_cache(self, request: Request) -> dict[str, bool]:
        """Drop all cached quotes."""
        await self.service.clear_cache()
        return {"ok": True}

    @post("/scenario/{name}")
    async def set_scenario(self, request: Request) -> JSONResponse:
        """Flip the simulated upstream health scenario."""
        raw = str(request.path_params["name"])
        try:
            scenario = Scenario(raw)
        except ValueError:
            valid = ", ".join(s.value for s in Scenario)
            return _problem(404, f"unknown scenario {raw!r}; valid: {valid}")
        self.faults.set(scenario)
        return JSONResponse({"ok": True, "scenario": scenario.value})


__all__ = ["RatesApiController"]
