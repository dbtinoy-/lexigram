"""Shared test configuration and fixtures for lexigram-ui tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest


@pytest.fixture
def render() -> Callable[..., str]:
    """Render a component to its HTML string representation.

    Usage:
        def test_button(render: Callable[..., str]) -> None:
            html = render(Button("Save"))
            assert "Save" in html
    """
    from lexigram.ui.core.base import render_to_string

    def _render(component: Any) -> str:
        return render_to_string(component)

    return _render


@pytest.fixture
def make_modal() -> Callable[..., Any]:
    """Create a Modal component with sensible defaults.

    Usage:
        def test_modal(make_modal: Callable[..., Any]) -> None:
            modal = make_modal(title="Confirm")
            assert "Confirm" in str(modal)
    """
    from lexigram.ui.molecules.modal import Modal

    def _make(title: str = "Test Title", **kwargs: Any) -> Any:
        return Modal(title=title, trigger=kwargs.pop("trigger", "Open"), **kwargs)

    return _make


@pytest.fixture
def make_alert() -> Callable[..., Any]:
    """Create an Alert component with sensible defaults.

    Usage:
        def test_alert(make_alert: Callable[..., Any]) -> None:
            alert = make_alert("Operation complete")
            assert "Operation complete" in str(alert)
    """
    from lexigram.ui.molecules.alert import Alert

    def _make(message: str = "Test message", **kwargs: Any) -> Any:
        return Alert(message=message, **kwargs)

    return _make


@pytest.fixture
def make_toast() -> Callable[..., Any]:
    """Create a Toast component with sensible defaults.

    Usage:
        def test_toast(make_toast: Callable[..., Any]) -> None:
            toast = make_toast("Saved successfully")
            assert "Saved successfully" in str(toast)
    """
    from lexigram.ui.molecules.toast import InlineToast

    def _make(message: str = "Test notification", **kwargs: Any) -> Any:
        return InlineToast(message=message, **kwargs)

    return _make
