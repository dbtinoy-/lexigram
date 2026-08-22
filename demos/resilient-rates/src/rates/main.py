"""Entry point for the resilient rates demo.

Usage::

    uv run python -m rates fetch EUR/USD
    uv run python -m rates scenario flaky
    uv run python -m rates stats
    uv run python -m rates stampede USD/JPY
    uv run python -m rates demo
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from lexigram.app import Application
from lexigram.logging import get_logger
from rates.module import RatesModule
from rates.provider import FaultController, Scenario
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
        "serve", help="serve the REST API (default :7073, RATES_PORT)"
    )
    p_serve.add_argument("--port", type=int, default=None)
    return parser


async def _fetch_and_print(service: RatesService, pair: str) -> int:
    result = await service.fetch(pair)
    if result.is_err():
        print(f"unavailable: {result.unwrap_err()}")
        return 1
    quote = result.unwrap()
    print(f"{quote.pair}\t{quote.rate}\tsource={quote.source}")
    return 0


async def _serve(port: int) -> None:
    from lexigram.web.di.provider import WebProvider
    from lexigram.web.server.runner import run_server_async

    async with Application.boot(
        name="rates", modules=[RatesModule.configure(port=port)]
    ) as app:
        await app.container.resolve(RatesService)  # eager pipeline wiring
        web = await app.container.resolve(WebProvider)
        await run_server_async(web.starlette, host="127.0.0.1", port=port)


async def _run(args: argparse.Namespace) -> None:
    if args.command == "serve":
        port = args.port or int(os.environ.get("RATES_PORT", "7073"))
        await _serve(port)
        return
    async with Application.boot(name="rates", modules=[RatesModule.configure()]) as app:
        service = await app.container.resolve(RatesService)
        faults = await app.container.resolve(FaultController)

        if args.command == "fetch":
            await _fetch_and_print(service, args.pair)
        elif args.command == "scenario":
            faults.set(Scenario(args.name))
            print(f"scenario: {args.name}")
        elif args.command == "stats":
            s = service.stats()
            print(
                f"hits={s.hits} misses={s.misses} upstream={s.upstream_calls} retries={s.retries} stale={s.stale_served}"
            )
        elif args.command == "clear-cache":
            await service.clear_cache()
            print("cache cleared")
        elif args.command == "stampede":
            await service.clear_cache()
            results = await asyncio.gather(
                *(service.fetch(args.pair) for _ in range(args.workers))
            )
            quotes = [r.unwrap() for r in results if r.is_ok()]
            unique = {q.rate for q in quotes}
            s = service.stats()
            print(
                f"{args.workers} concurrent fetchers saw {len(unique)} distinct rate(s)"
            )
            print(f"upstream calls: {s.upstream_calls}")
        elif args.command == "demo":
            await _demo(service, faults)


def _banner(act: int, title: str) -> None:
    print(f"\n=== act {act}: {title} ===")


async def _demo(service: RatesService, faults: FaultController) -> None:
    """Five deterministic acts narrating resilience + cache behavior."""
    service.reset_stats()
    await service.clear_cache()

    _banner(1, "healthy — cache-aside")
    await _fetch_and_print(service, "EUR/USD")  # miss -> upstream
    await _fetch_and_print(service, "EUR/USD")  # cache hit

    _banner(2, "flaky — retries absorb timeouts")
    faults.set(Scenario.FLAKY)
    for _attempt in range(6):
        try:
            await _fetch_and_print(service, "GBP/USD")
        except Exception as exc:  # noqa: BLE001 — narration of terminal outcome
            print(f"upstream exhausted: {type(exc).__name__}")
        if service.stats().retries > 0:
            break
    print(f"retry attempts absorbed by backoff: {service.stats().retries}")

    _banner(3, "down — breaker opens, stale serves reads")
    faults.set(Scenario.DOWN)
    await service.clear_cache()  # simulate TTL expiry so reads reach the breaker
    for _ in range(3):
        try:
            (await service.fetch("EUR/USD")).unwrap()
        except Exception as exc:  # noqa: BLE001 — narration of terminal outcome
            print(f"upstream exhausted: {type(exc).__name__}")
    stale_result = await service.fetch("EUR/USD")
    if stale_result.is_err():
        # No stale tier exists yet — the outage surfaces to the caller.
        print(f"unavailable: {stale_result.unwrap_err()}")
        faults.set(Scenario.HEALTHY)
        return
    stale = stale_result.unwrap()
    print(f"{stale.pair}\t{stale.rate}\tsource={stale.source}")

    _banner(4, "heal — HALF_OPEN probe closes the circuit")
    faults.set(Scenario.HEALTHY)
    await service.clear_cache()  # fresh read must probe the recovering circuit
    await asyncio.sleep(0.25)  # past the 0.2s recovery window
    healed = (await service.fetch("EUR/USD")).unwrap()
    print(f"circuit CLOSED after HALF_OPEN probe; source={healed.source}")

    _banner(5, "stampede — single-flight collapses 10 into 1")
    await service.clear_cache()
    service.reset_stats()
    results = await asyncio.gather(*(service.fetch("USD/JPY") for _ in range(10)))
    quotes = [r.unwrap() for r in results if r.is_ok()]
    print(f"distinct rates seen: {len({q.rate for q in quotes})}")
    print(f"upstream calls: {service.stats().upstream_calls}")
    print("single-flight: 10 waiters, 1 leader")

    faults.set(Scenario.HEALTHY)


def main() -> None:
    args = _build_parser().parse_args()
    try:
        asyncio.run(_run(args))
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
