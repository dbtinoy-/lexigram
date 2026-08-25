"""Tests for the rate desk CLI commands (structured-logging narration)."""

from __future__ import annotations

import pytest
from structlog.testing import capture_logs

from rates.cli import build_parser, run


@pytest.fixture(autouse=True)
def _freeze_logging_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep structlog processors stable so capture_logs sees events.

    ``Application.__init__`` applies LoggingConfig on every boot, replacing
    the processor chain mid-test; these CLI tests do not exercise rendering.
    """
    monkeypatch.setattr(
        "lexigram.app.base._apply_logging_config", lambda _cfg: None
    )


async def test_fetch_logs_quote() -> None:
    args = build_parser().parse_args(["fetch", "EUR/USD"])
    with capture_logs() as events:
        await run(args)

    event = next(e for e in events if e["event"] == "quote.fetched")
    assert event["pair"] == "EUR/USD"
    assert event["source"] == "upstream"


async def test_scenario_command_sets_fault() -> None:
    args = build_parser().parse_args(["scenario", "flaky"])
    with capture_logs() as events:
        await run(args)

    assert any(e["event"] == "scenario.set" for e in events)


async def test_demo_walks_all_five_acts() -> None:
    args = build_parser().parse_args(["demo"])
    with capture_logs() as events:
        await run(args)

    acts = {e["act"] for e in events if e["event"] == "act.start"}
    assert acts == {1, 2, 3, 4, 5}
    names = [e["event"] for e in events]
    assert "quote.stale_served" in names
    assert "circuit.closed_after_probe" in names
    stampede = next(e for e in events if e["event"] == "stampede.completed")
    assert stampede["distinct_rates"] == 1
    assert stampede["upstream_calls"] == 1


@pytest.mark.parametrize(
    ("command", "event"),
    [("stats", "stats.reported"), ("clear-cache", "cache.cleared")],
)
async def test_utility_commands_log_events(command: str, event: str) -> None:
    args = build_parser().parse_args([command])
    with capture_logs() as events:
        await run(args)

    assert any(e["event"] == event for e in events)
