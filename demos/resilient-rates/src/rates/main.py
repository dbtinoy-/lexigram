"""Entry point for the resilient rates demo.

Usage::

    uv run python -m rates fetch EUR/USD
    uv run python -m rates scenario flaky
    uv run python -m rates stats
    uv run python -m rates stampede USD/JPY
    uv run python -m rates demo

Server host/port come from ``application.yaml`` (``web.server``); override
without editing the file via ``LEX_WEB__SERVER__PORT``.
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Awaitable, Callable
import sys
from typing import Any

from lexigram.app import Application
from lexigram.config.main import LexigramConfig
from lexigram.logging import get_logger
from lexigram.web.config import WebConfig
from rates.config import APP_YAML
from rates.module import RatesModule
from rates.repository.simulated_upstream import FaultController, Scenario
from rates.services.rates_service import RatesService

logger = get_logger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rates", description="Forex rate desk (resilience + cache)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_fetch = sub.add_parser("fetch", help="fetch one pair")
    p_fetch.add_argument("pair")

    p_scn = sub.add_parser("scenario", help="flip upstream health")
    p_scn.add_argument("name", choices=[s.value for s in Scenario])

    sub.add_parser("stats", help="print counters")
    sub.add_parser("clear-cache", help="drop cached quotes")

    p_stm = sub.add_parser("stampede", help="N concurrent fetches of one pair")
    p_stm.add_argument("pair")
    p_stm.add_argument("--workers", type=int, default=10)

    sub.add_parser("demo", help="five-act guided walkthrough")
    p_serve = sub.add_parser(
        "serve", help="serve the REST API (:7073 from application.yaml)"
    )
    return parser


def _bind(
    config: LexigramConfig | None,
) -> tuple[WebConfig, LexigramConfig]:
    """Bind web/demo sections from the given or demo-default config."""
    resolved = config or LexigramConfig.from_yaml(APP_YAML)
    return resolved.get_section("web", WebConfig), resolved


async def _fetch_and_log(service: RatesService, pair: str) -> int:
    result = await service.fetch(pair)
    if result.is_err():
        logger.error("quote.unavailable", pair=pair, error=str(result.unwrap_err()))
        return 1
    quote = result.unwrap()
    logger.info(
        "quote.fetched", pair=quote.pair, rate=str(quote.rate), source=quote.source
    )
    return 0


async def _serve(config: LexigramConfig | None = None) -> None:
    from lexigram.web.di.provider import WebProvider
    from lexigram.web.server.runner import run_server_async

    web_config, _resolved = _bind(config)
    async with Application.boot(
        name="rates", modules=[RatesModule.configure()], config=_resolved
    ) as app:
        web = await app.container.resolve(WebProvider)
        await run_server_async(
            web.starlette,
            host=web_config.server.host,
            port=web_config.server.port,
        )


async def _run(args: argparse.Namespace, config: LexigramConfig | None = None) -> None:
    if args.command == "serve":
        await _serve(config)
        return
    _web_config, resolved = _bind(config)
    async with Application.boot(
        name="rates", modules=[RatesModule.configure()], config=resolved
    ) as app:
        service = await app.container.resolve(RatesService)
        faults = await app.container.resolve(FaultController)

        # Registry dispatch (AGENTS §4.1): no if/elif chain.
        async def _scenario() -> None:
            faults.set(Scenario(args.name))
            logger.info("scenario.set", name=args.name)

        async def _stats() -> None:
            s = service.stats()
            logger.info(
                "stats.reported",
                hits=s.hits,
                misses=s.misses,
                upstream=s.upstream_calls,
                retries=s.retries,
                stale_served=s.stale_served,
            )

        commands: dict[str, Callable[[], Awaitable[Any]]] = {
            "fetch": lambda: _fetch_and_log(service, args.pair),
            "scenario": _scenario,
            "stats": _stats,
            "clear-cache": lambda: _clear_cache(service),
            "stampede": lambda: _stampede(service, args.pair, args.workers),
            "demo": lambda: _demo(service, faults),
        }
        await commands[args.command]()


async def _stampede(
    service: RatesService,
    pair: str,
    workers: int,
    note: str | None = None,
) -> None:
    """Collapse N concurrent fetches of one pair into a single upstream call."""
    await service.clear_cache()
    results = await asyncio.gather(*(service.fetch(pair) for _ in range(workers)))
    quotes = [r.unwrap() for r in results if r.is_ok()]
    s = service.stats()
    logger.info(
        "stampede.completed",
        workers=workers,
        distinct_rates=len({q.rate for q in quotes}),
        upstream_calls=s.upstream_calls,
        **({"note": note} if note else {}),
    )


async def _clear_cache(service: RatesService) -> None:
    """Drop cached quotes and report."""
    await service.clear_cache()
    logger.info("cache.cleared")


def _banner(act: int, title: str) -> None:
    logger.info("act.start", act=act, title=title)


async def _demo(service: RatesService, faults: FaultController) -> None:
    """Five deterministic acts narrating resilience + cache behavior."""
    service.reset_stats()
    await service.clear_cache()

    _banner(1, "healthy — cache-aside")
    await _fetch_and_log(service, "EUR/USD")  # miss -> upstream
    await _fetch_and_log(service, "EUR/USD")  # cache hit

    _banner(2, "flaky — retries absorb timeouts")
    faults.set(Scenario.FLAKY)
    for _attempt in range(6):
        try:
            await _fetch_and_log(service, "GBP/USD")
        except Exception as exc:  # noqa: BLE001 — narration of terminal outcome
            logger.warning("upstream.exhausted", error=type(exc).__name__)
        if service.stats().retries > 0:
            break
    logger.info("retries.absorbed", count=service.stats().retries)

    _banner(3, "down — breaker opens, stale serves reads")
    faults.set(Scenario.DOWN)
    await service.clear_cache()  # simulate TTL expiry so reads reach the breaker
    for _ in range(3):
        try:
            (await service.fetch("EUR/USD")).unwrap()
        except Exception as exc:  # noqa: BLE001 — narration of terminal outcome
            logger.warning("upstream.exhausted", error=type(exc).__name__)
    stale_result = await service.fetch("EUR/USD")
    if stale_result.is_err():
        # No stale tier exists yet — the outage surfaces to the caller.
        logger.error("quote.unavailable", error=str(stale_result.unwrap_err()))
        faults.set(Scenario.HEALTHY)
        return
    stale = stale_result.unwrap()
    logger.info(
        "quote.stale_served", pair=stale.pair, rate=str(stale.rate), source=stale.source
    )

    _banner(4, "heal — HALF_OPEN probe closes the circuit")
    faults.set(Scenario.HEALTHY)
    await service.clear_cache()  # fresh read must probe the recovering circuit
    await asyncio.sleep(0.25)  # past the 0.2s recovery window
    healed = (await service.fetch("EUR/USD")).unwrap()
    logger.info("circuit.closed_after_probe", source=healed.source)

    _banner(5, "stampede — single-flight collapses 10 into 1")
    service.reset_stats()
    await _stampede(
        service, "USD/JPY", workers=10, note="single-flight: 10 waiters, 1 leader"
    )

    faults.set(Scenario.HEALTHY)


def main() -> None:
    args = _build_parser().parse_args()
    try:
        asyncio.run(_run(args))
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
