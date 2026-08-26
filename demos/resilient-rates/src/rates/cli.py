"""Interactive teaching CLI for the resilient-rates demo.

Public surface: :func:`build_parser` and :func:`main`. Every command boots the
real application via ``rates.app.create_app`` and narrates behavior through
structured events.
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Awaitable, Callable

from lexigram.logging import get_logger
from rates.app import create_app
from rates.repository.simulated_upstream import FaultController, Scenario
from rates.services.rates_service import RatesService

logger = get_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build the ``rates`` command-line parser."""
    parser = argparse.ArgumentParser(
        prog="rates", description="Forex rate desk (resilience + cache)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser("fetch", help="fetch one pair")
    fetch.add_argument("pair")

    scenario = sub.add_parser("scenario", help="flip upstream health")
    scenario.add_argument("name", choices=[s.value for s in Scenario])

    sub.add_parser("stats", help="report counters")
    sub.add_parser("clear-cache", help="drop cached quotes")

    stampede = sub.add_parser("stampede", help="N concurrent fetches of one pair")
    stampede.add_argument("pair")
    stampede.add_argument("--workers", type=int, default=10)

    sub.add_parser("demo", help="five-act guided walkthrough")
    return parser


async def fetch_and_log(service: RatesService, pair: str) -> int:
    """Fetch one quote and narrate the outcome; returns an exit code."""
    result = await service.fetch(pair)
    if result.is_err():
        logger.error("quote.unavailable", pair=pair, error=str(result.unwrap_err()))
        return 1
    quote = result.unwrap()
    logger.info(
        "quote.fetched", pair=quote.pair, rate=str(quote.rate), source=quote.source
    )
    return 0


async def stampede(
    service: RatesService, pair: str, workers: int, note: str | None = None
) -> None:
    """Collapse N concurrent fetches of one pair into a single upstream call."""
    await service.clear_cache()
    results = await asyncio.gather(*(service.fetch(pair) for _ in range(workers)))
    quotes = [r.unwrap() for r in results if r.is_ok()]
    logger.info(
        "stampede.completed",
        workers=workers,
        distinct_rates=len({q.rate for q in quotes}),
        upstream_calls=service.stats().upstream_calls,
        **({"note": note} if note else {}),
    )


def banner(act: int, title: str) -> None:
    logger.info("act.start", act=act, title=title)


async def five_act_demo(service: RatesService, faults: FaultController) -> None:
    """Five deterministic acts narrating resilience + cache behavior."""
    service.reset_stats()
    await service.clear_cache()

    banner(1, "healthy — cache-aside")
    await fetch_and_log(service, "EUR/USD")  # miss -> upstream
    await fetch_and_log(service, "EUR/USD")  # cache hit

    banner(2, "flaky — retries absorb timeouts")
    faults.set(Scenario.FLAKY)
    for _attempt in range(6):
        try:
            await fetch_and_log(service, "GBP/USD")
        except Exception as exc:  # noqa: BLE001 — narration of terminal outcome
            logger.warning("upstream.exhausted", error=type(exc).__name__)
        if service.stats().retries > 0:
            break
    logger.info("retries.absorbed", count=service.stats().retries)

    banner(3, "down — breaker opens, stale serves reads")
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

    banner(4, "heal — HALF_OPEN probe closes the circuit")
    faults.set(Scenario.HEALTHY)
    await service.clear_cache()  # fresh read must probe the recovering circuit
    await asyncio.sleep(0.25)  # past the 0.2s recovery window
    healed = (await service.fetch("EUR/USD")).unwrap()
    logger.info("circuit.closed_after_probe", source=healed.source)

    banner(5, "stampede — single-flight collapses 10 into 1")
    service.reset_stats()
    await stampede(
        service, "USD/JPY", workers=10, note="single-flight: 10 waiters, 1 leader"
    )

    faults.set(Scenario.HEALTHY)


async def run(args: argparse.Namespace) -> int:
    """Dispatch the parsed command; returns the process exit code."""
    app = create_app()
    try:
        await app.start()
        service = await app.container.resolve(RatesService)
        faults = await app.container.resolve(FaultController)

        async def do_scenario() -> None:
            faults.set(Scenario(args.name))
            logger.info("scenario.set", name=args.name)

        async def do_stats() -> None:
            s = service.stats()
            logger.info(
                "stats.reported",
                hits=s.hits,
                misses=s.misses,
                upstream=s.upstream_calls,
                retries=s.retries,
                stale_served=s.stale_served,
            )

        async def do_clear_cache() -> None:
            await service.clear_cache()
            logger.info("cache.cleared")

        commands: dict[str, Callable[[], Awaitable[object]]] = {
            "fetch": lambda: fetch_and_log(service, args.pair),
            "scenario": do_scenario,
            "stats": do_stats,
            "clear-cache": do_clear_cache,
            "stampede": lambda: stampede(service, args.pair, args.workers),
            "demo": lambda: five_act_demo(service, faults),
        }
        outcome = await commands[args.command]()
        return int(outcome) if isinstance(outcome, int) else 0
    finally:
        await app.stop()


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; returns the process exit code."""
    args = build_parser().parse_args(argv)
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        return 130


__all__ = ["build_parser", "five_act_demo", "main", "run"]
