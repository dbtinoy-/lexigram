"""Tests for ErrorBoundary molecule."""
from __future__ import annotations

from lexigram.ui.core.base import Component, el
from lexigram.ui.molecules.error_boundary import ErrorBoundary


class TestErrorBoundary:
    def test_renders_children_normally(self) -> None:
        boundary = ErrorBoundary()
        boundary.children = [el("span", "Hello")]
        result = str(boundary)
        assert "Hello" in result

    def test_catches_render_error_uses_default_fallback(self) -> None:
        class Broken(Component):
            def render(self):
                msg = "broken"
                raise RuntimeError(msg)

        boundary = ErrorBoundary()
        boundary.children = [Broken()]
        result = str(boundary)
        assert "Rendering Error" in result

    def test_catches_render_error_uses_custom_fallback(self) -> None:
        class Broken(Component):
            def render(self):
                raise RuntimeError("broken")

        boundary = ErrorBoundary(fallback=el("div", "Custom Error"))
        boundary.children = [Broken()]
        result = str(boundary)
        assert "Custom Error" in result
        assert "Rendering Error" not in result
