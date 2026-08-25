"""Entry points for the feedback-loop demo.

Run::

    PYTHONPATH=demos/feedback-loop/src uv run python -m feedback_loop demo
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from feedback_loop.app import create_app
from feedback_loop.config import load_lex_config
from feedback_loop.repository.bot import BOT, TRACE_IDS
from feedback_loop.services.loop_service import LoopService


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--experiment-dir",
        default=".runs",
        help="Tracker/checkpoint root (default: .runs)",
    )
    parser = argparse.ArgumentParser(prog="feedback_loop", parents=[common])
    sub = parser.add_subparsers(dest="command", required=True)

    p_ask = sub.add_parser(
        "ask",
        help="ask a canned question",
        parents=[common],
    )
    p_ask.add_argument("key")
    p_ask.add_argument("--owner", required=True)

    p_rate = sub.add_parser("rate", help="rate a trace 1..5", parents=[common])
    p_rate.add_argument("trace_id")
    p_rate.add_argument("rating", type=float)
    p_rate.add_argument("--comment", default=None)
    p_rate.add_argument("--owner", required=True)

    p_stats = sub.add_parser(
        "stats",
        help="aggregate my ratings",
        parents=[common],
    )
    p_stats.add_argument("--owner", required=True)

    p_reg = sub.add_parser(
        "regress",
        help="run regression from low ratings",
        parents=[common],
    )
    p_reg.add_argument("--owner", required=True)

    p_rep = sub.add_parser(
        "report",
        help="error analysis for a run",
        parents=[common],
    )
    p_rep.add_argument("run_id")

    sub.add_parser(
        "demo",
        help="full loop: asks, ratings, regress, report",
        parents=[common],
    )
    return parser


def _err_exit(result) -> int:
    """Print a domain error and signal failure."""
    if result.is_err():
        print(f"error: {result.unwrap_err()}")
        return 1
    return 0


async def run(args: argparse.Namespace) -> int:
    """Dispatch the parsed command against one booted application."""
    app = create_app(
        load_lex_config().model_copy(
            update={"experiment_dir": args.experiment_dir}, deep=True
        )
        if hasattr(args, "experiment_dir")
        else load_lex_config()
    )
    try:
        await app.start()
        service = await app.container.resolve(LoopService)
        if args.command == "demo":
            return await _demo(service)
        return await _single(service, args)
    finally:
        await app.stop()


async def _serve(web_config) -> int:
    """Serve the web console until interrupted."""
    from lexigram.web.di.provider import WebProvider
    from lexigram.web.server.runner import run_server_async

    web = await app.container.resolve(WebProvider)
    print(f"serving on http://127.0.0.1:{port}")
    await run_server_async(
        web.starlette, host=web_config.server.host, port=web_config.server.port
    )
    return 0


async def _single(service: LoopService, args: argparse.Namespace) -> int:
    if args.command == "ask":
        result = await service.ask(args.key, owner=args.owner)
        if result.is_err():
            return _err_exit(result)
        answer = result.unwrap()
        print(f"[{answer.trace_id}] {answer.answer}")
        print(
            f"rate it:  feedback_loop rate {answer.trace_id} <1-5> --owner {args.owner}"
        )
    elif args.command == "rate":
        rate_result = await service.rate(
            args.trace_id,
            args.rating,
            owner=args.owner,
            comment=args.comment,
        )
        if rate_result.is_err():
            return _err_exit(rate_result)
        print(f"captured rating {args.rating:g} ({rate_result.unwrap()})")
    elif args.command == "stats":
        snap = await service.stats(owner=args.owner)
        avg = snap.average if snap.average is not None else "n/a"
        print(f"total={snap.total} average={avg} by_type={snap.by_type}")
    elif args.command == "regress":
        regress_result = await service.regress(owner=args.owner)
        if regress_result.is_err():
            return _err_exit(regress_result)
        summary = regress_result.unwrap()
        print(f"run={summary.run_id}")
        print(
            f"samples={summary.total_samples} "
            f"passed={summary.passed_samples} "
            f"average={summary.average_score}"
        )
        print(f"failing: {', '.join(summary.failing_ids) or '(none)'}")
    elif args.command == "report":
        analysis = await service.report(args.run_id)
        print(f"records={analysis.total_records} errors={analysis.error_count}")
        print(
            f"score mean={analysis.score_mean} min={analysis.score_min} "
            f"max={analysis.score_max}"
        )
    return 0


async def _demo(service: LoopService) -> int:
    ratings = {
        "refund-policy": 1.0,
        "shipping-time": 2.0,
        "track-order": 5.0,
        "warranty": 4.0,
    }

    print("== ask ==")
    for key in sorted(BOT):
        result = await service.ask(key, owner="alice")
        if result.is_err():
            return _err_exit(result)
        answer = result.unwrap()
        print(f"[{answer.trace_id}] {key}: {answer.answer}")

    print("\n== rate ==")
    for key, value in ratings.items():
        rated = await service.rate(
            TRACE_IDS[key],
            value,
            owner="alice",
            comment=f"auto:{value:g}",
        )
        if rated.is_err():
            return _err_exit(rated)
        print(f"{TRACE_IDS[key]} <- {value:g} ({rated.unwrap()})")

    print("\n== stats ==")
    snap = await service.stats(owner="alice")
    avg = snap.average if snap.average is not None else "n/a"
    print(f"total={snap.total} average={avg} by_type={snap.by_type}")

    print("\n== regress ==")
    regressed = await service.regress(owner="alice")
    if regressed.is_err():
        return _err_exit(regressed)
    summary = regressed.unwrap()
    print(f"run={summary.run_id}")
    print(
        f"samples={summary.total_samples} passed={summary.passed_samples} "
        f"average={summary.average_score}"
    )
    print(f"failing: {', '.join(summary.failing_ids)}")

    print("\n== report ==")
    analysis = await service.report(summary.run_id)
    print(f"records={analysis.total_records} errors={analysis.error_count}")
    return 0


def main() -> int:
    args = build_parser().parse_args()
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
