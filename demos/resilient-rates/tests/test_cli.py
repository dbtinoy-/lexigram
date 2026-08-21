"""Tests for the rate desk CLI commands."""

from __future__ import annotations

import contextlib
import io

from rates.main import _build_parser, _run


async def test_fetch_prints_quote() -> None:
    buffer = io.StringIO()
    args = _build_parser().parse_args(["fetch", "EUR/USD"])
    with contextlib.redirect_stdout(buffer):
        await _run(args)

    out = buffer.getvalue()
    assert "EUR/USD" in out
    assert "source=upstream" in out


async def test_demo_walks_all_five_acts() -> None:
    buffer = io.StringIO()
    args = _build_parser().parse_args(["demo"])
    with contextlib.redirect_stdout(buffer):
        await _run(args)

    out = buffer.getvalue()
    for marker in (
        "act 1:",
        "act 2:",
        "act 3:",
        "act 4:",
        "act 5:",
        "source=cache",
        "retry",
        "source=stale",
        "HALF_OPEN",
        "single-flight",
        "upstream calls: 1",
    ):
        assert marker in out, f"missing narration marker: {marker}"
