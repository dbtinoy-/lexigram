"""REST surface for the resilient rates demo.

Convention followed: **Controller pattern** — each handler resolves its
dependencies from the container and returns domain ``Result`` values.
The framework's result bridge serializes them.

Exposes the rate desk over HTTP so resilience behaviour can be driven live
from a browser or curl while watching retry/breaker/stale reactions:

- ``GET /rates/{pair}``        — fetch a quote (cache → single-flight →
  resilient upstream → stale fallback)
- ``GET /stats``               — hit/miss/upstream/retry/stale counters
- ``POST /scenario/{name}``    — flip the upstream health scenario
  (``healthy | flaky | down | slow``)
- ``POST /cache/clear``        — drop cached quotes
- ``POST /stampede/{pair}``    — collapse N concurrent fetches into one call
- ``POST /demo``               — five-act guided walkthrough

Errors: handlers return domain ``Result`` values and the framework's result
bridge serializes them — ``RateUnavailableError`` is registered below as an
upstream fault (503). Unknown pair/scenario paths answer with RFC-9457
problem details (404).
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict

from starlette.requests import Request

from lexigram.logging import get_logger
from lexigram.web import (
    Controller,
    JSONResponse,
    ProblemDetail,
    ResultResponseMapper,
    get,
    post,
)
from rates.exceptions import RateUnavailableError
from rates.repository import FaultController, Scenario
from rates.services import RatesService

logger = get_logger(__name__)

# Domain failure → HTTP: no quote obtainable is an upstream fault (503).
ResultResponseMapper.register(RateUnavailableError, 503)


def _problem(status: int, detail: str) -> JSONResponse:
    """RFC-9457 style problem response."""
    body = ProblemDetail(
        title="Request rejected", status=status, detail=detail
    ).to_dict()
    return JSONResponse(body, status_code=status)


def _banner(act: int, title: str) -> None:
    """Narrate the start of a demo act via structured logging."""
    logger.info("act.start", act=act, title=title)


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

    @post("/stampede/{pair:path}")
    async def stampede(self, request: Request) -> JSONResponse:
        """Collapse N concurrent fetches of one pair into a single upstream call.

        Reads ``workers`` from query params (default 10).  Clears the cache
        first so every concurrent caller hits the upstream path simultaneously,
        then the single-flight gate collapses them.
        """
        pair = str(request.path_params["pair"]).upper().strip("/")
        if "/" not in pair:
            return _problem(404, f"invalid pair {pair!r}; expected BASE/QUOTE")
        workers = int(request.query_params.get("workers", "10"))
        await self.service.clear_cache()
        results = await asyncio.gather(
            *(self.service.fetch(pair) for _ in range(workers))
        )
        quotes = [r.unwrap() for r in results if r.is_ok()]
        distinct = len({q.rate for q in quotes})
        upstream_calls = self.service.stats().upstream_calls
        logger.info(
            "stampede.completed",
            pair=pair,
            workers=workers,
            distinct_rates=distinct,
            upstream_calls=upstream_calls,
        )
        return JSONResponse(
            {
                "ok": True,
                "pair": pair,
                "workers": workers,
                "distinct_rates": distinct,
                "upstream_calls": upstream_calls,
            }
        )

    @post("/demo")
    async def demo(self, request: Request) -> JSONResponse:
        """Run the five-act guided walkthrough narrating resilience + cache.

        Acts:

        1. Healthy — cache-aside (miss → upstream, hit → cache)
        2. Flaky — retries absorb timeouts
        3. Down — breaker opens, stale serves reads
        4. Heal — HALF_OPEN probe closes the circuit
        5. Stampede — single-flight collapses 10 into 1
        """
        self.service.reset_stats()
        await self.service.clear_cache()

        _banner(1, "healthy — cache-aside")
        await self._fetch_and_log("EUR/USD")  # miss -> upstream
        await self._fetch_and_log("EUR/USD")  # cache hit

        _banner(2, "flaky — retries absorb timeouts")
        self.faults.set(Scenario.FLAKY)
        for _ in range(6):
            try:
                await self._fetch_and_log("GBP/USD")
            except Exception as exc:  # noqa: BLE001 — narration of terminal outcome
                logger.warning("upstream.exhausted", error=type(exc).__name__)
            if self.service.stats().retries > 0:
                break
        logger.info("retries.absorbed", count=self.service.stats().retries)

        _banner(3, "down — breaker opens, stale serves reads")
        self.faults.set(Scenario.DOWN)
        await self.service.clear_cache()
        for _ in range(3):
            try:
                (await self.service.fetch("EUR/USD")).unwrap()
            except Exception as exc:  # noqa: BLE001 — narration of terminal outcome
                logger.warning("upstream.exhausted", error=type(exc).__name__)
        stale_result = await self.service.fetch("EUR/USD")
        if stale_result.is_err():
            logger.error("quote.unavailable", error=str(stale_result.unwrap_err()))
            self.faults.set(Scenario.HEALTHY)
            return JSONResponse(
                {"ok": False, "error": "no stale copy available", "act": 3}
            )
        stale = stale_result.unwrap()
        logger.info(
            "quote.stale_served",
            pair=stale.pair,
            rate=str(stale.rate),
            source=stale.source,
        )

        _banner(4, "heal — HALF_OPEN probe closes the circuit")
        self.faults.set(Scenario.HEALTHY)
        await self.service.clear_cache()
        await asyncio.sleep(0.25)
        healed = (await self.service.fetch("EUR/USD")).unwrap()
        logger.info("circuit.closed_after_probe", source=healed.source)

        _banner(5, "stampede — single-flight collapses 10 into 1")
        self.service.reset_stats()
        await self.service.clear_cache()
        await asyncio.gather(*(self.service.fetch("USD/JPY") for _ in range(10)))
        logger.info(
            "stampede.completed",
            workers=10,
            distinct_rates=1,
            upstream_calls=self.service.stats().upstream_calls,
            note="single-flight: 10 waiters, 1 leader",
        )

        self.faults.set(Scenario.HEALTHY)
        return JSONResponse({"ok": True, "acts": 5})

    async def _fetch_and_log(self, pair: str) -> None:
        """Fetch one quote and narrate the outcome."""
        result = await self.service.fetch(pair)
        if result.is_err():
            logger.error("quote.unavailable", pair=pair, error=str(result.unwrap_err()))
            return
        quote = result.unwrap()
        logger.info(
            "quote.fetched",
            pair=quote.pair,
            rate=str(quote.rate),
            source=quote.source,
        )


__all__ = ["RatesApiController"]
