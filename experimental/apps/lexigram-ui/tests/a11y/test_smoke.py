"""Smoke test: Playwright can launch and load a data: URL."""

from __future__ import annotations


def test_playwright_launches(page: object) -> None:
    """Verify the Playwright page fixture works at all."""
    page.set_content("<h1>hello</h1>")  # type: ignore[attr-defined]
    assert page.locator("h1").inner_text() == "hello"  # type: ignore[attr-defined]