"""Tests for the offline event-driven-orders walkthrough entry point."""

from __future__ import annotations

from orders.main import run_cli_demo


async def test_cli_demo_completes_without_starting_a_server() -> None:
    """The documented demo command runs the full order lifecycle and returns."""
    await run_cli_demo()
