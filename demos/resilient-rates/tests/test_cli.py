"""Tests for the offline resilient-rates walkthrough entry point."""

from __future__ import annotations

from rates.main import run_cli_demo


async def test_cli_demo_completes_without_starting_a_server() -> None:
    """The documented demo command runs all five acts and returns."""
    await run_cli_demo()
