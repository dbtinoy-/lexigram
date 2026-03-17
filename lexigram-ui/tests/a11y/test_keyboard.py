"""Keyboard and focus behavior for interactive components."""

from __future__ import annotations

import pytest


def test_modal_escape_closes(page: object, gallery: dict[str, str]) -> None:
    """Escape must close the dialog (WCAG 2.2: no keyboard traps)."""
    page.set_content(gallery["Modal"])  # type: ignore[attr-defined]
    page.keyboard.press("Escape")  # type: ignore[attr-defined]
    dialog_visible = page.locator('[role="dialog"]:visible').count()  # type: ignore[attr-defined]
    assert dialog_visible == 0


def test_modal_focus_trap(page: object, gallery: dict[str, str]) -> None:
    """Tab cycling must stay inside the dialog (x-trap)."""
    page.set_content(gallery["Modal"])  # type: ignore[attr-defined]
    page.wait_for_timeout(300)  # let Alpine mount and trap focus
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
    page.wait_for_timeout(300)  # let Alpine mount and trap focus
    page.locator("button").first.focus()  # type: ignore[attr-defined]
    page.keyboard.press("Escape")  # type: ignore[attr-defined]
    page.wait_for_timeout(300)  # let Alpine release the focus trap
    page.keyboard.press("Tab")  # type: ignore[attr-defined]
    focused_trigger = page.evaluate(  # type: ignore[attr-defined]
        "() => document.activeElement && document.activeElement.textContent.trim() === 'Open'"
    )
    assert focused_trigger