"""Tests for the offline rag-docs walkthrough entry point."""

from __future__ import annotations

from rag_docs.main import run_cli_demo


async def test_cli_demo_completes_without_starting_a_server() -> None:
    """The documented demo command runs all three cited questions and returns."""
    await run_cli_demo()
