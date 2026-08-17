"""Keyboard and focus behavior for interactive components."""

from __future__ import annotations

import pytest


def _wait_alpine(page: object) -> None:
    """Block until Alpine has mounted (Tailwind CDN delays startup)."""
    page.wait_for_function(  # type: ignore[attr-defined]
        "() => typeof window.Alpine !== 'undefined'"
    )
    page.wait_for_timeout(300)  # type: ignore[attr-defined]  # let directives apply


def test_modal_escape_closes(page: object, gallery: dict[str, str]) -> None:
    """Escape must close the dialog (WCAG 2.2: no keyboard traps)."""
    page.set_content(gallery["Modal"])  # type: ignore[attr-defined]
    _wait_alpine(page)
    dialog = page.locator('[role="dialog"]')  # type: ignore[attr-defined]
    dialog.wait_for(state="visible")  # type: ignore[attr-defined]
    for _ in range(12):
        page.keyboard.press("Escape")  # type: ignore[attr-defined]
        page.wait_for_timeout(250)  # type: ignore[attr-defined]
        if dialog.count() == 0 or not dialog.is_visible():  # type: ignore[attr-defined]
            return
    pytest.fail("dialog stayed open after repeated Escape presses")


def test_modal_focus_trap(page: object, gallery: dict[str, str]) -> None:
    """Tab cycling must stay inside the dialog (x-trap)."""
    page.set_content(gallery["Modal"])  # type: ignore[attr-defined]
    _wait_alpine(page)
    page.keyboard.press("Tab")  # type: ignore[attr-defined]
    page.keyboard.press("Tab")
    page.keyboard.press("Tab")
    focused_in_dialog = page.evaluate(  # type: ignore[attr-defined]
        "() => document.activeElement && !!document.activeElement.closest('[role=dialog]')"
    )
    assert focused_in_dialog


def test_modal_focus_returns_to_trigger(page: object, gallery: dict[str, str]) -> None:
    """Focus must return to the trigger button when dialog closes."""
    page.set_content(gallery["Modal"])  # type: ignore[attr-defined]
    _wait_alpine(page)
    page.locator("button").first.focus()  # type: ignore[attr-defined]
    page.keyboard.press("Escape")  # type: ignore[attr-defined]
    page.wait_for_timeout(300)  # let Alpine release the focus trap
    page.keyboard.press("Tab")  # type: ignore[attr-defined]
    focused_trigger = page.evaluate(  # type: ignore[attr-defined]
        "() => document.activeElement && document.activeElement.textContent.trim() === 'Open'"
    )
    assert focused_trigger