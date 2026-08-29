"""Input atom decoration: help text and multi-error support.

``AbstractInput`` is the single wrapper for every text/select atom; label,
help text and every validation message must render in an accessible order
(label → input → help → errors) with ``aria`` wiring.
"""

from __future__ import annotations

from lexigram.ui import TextInput, render_to_string


class TestInputDecorations:
    def test_help_text_renders_below_input(self) -> None:
        field = TextInput(
            name="email",
            label="Email",
            help_text="We only use this for login.",
        )
        html = render_to_string(field)
        assert 'name="email"' in html
        assert "We only use this for login." in html
        assert 'id="email-help"' in html
        assert "type=\"text\"" in html

    def test_help_text_hidden_when_error_present(self) -> None:
        field = TextInput(
            name="email",
            label="Email",
            help_text="We only use this for login.",
            error="Invalid email",
        )
        html = render_to_string(field)
        assert "We only use this for login." not in html
        assert "Invalid email" in html
        assert 'role="alert"' in html

    def test_multiple_errors_render_one_paragraph_each(self) -> None:
        field = TextInput(
            name="email",
            error=["Invalid email", "Already taken"],
        )
        html = render_to_string(field)
        assert 'id="email-error"' in html
        assert 'id="email-error-2"' in html
        assert "Invalid email" in html
        assert "Already taken" in html
        assert html.count("role=\"alert\"") == 2
        assert "border-destructive" in html

    def test_single_string_error_keeps_legacy_markup(self) -> None:
        field = TextInput(name="name", error="Required")
        html = render_to_string(field)
        assert 'id="name-error"' in html
        assert 'role="alert"' in html
        assert "Required" in html

    def test_help_text_passes_through_wrapper_without_label(self) -> None:
        field = TextInput(name="code", help_text="Format: ABC-123")
        html = render_to_string(field)
        assert 'id="code-help"' in html
        assert "Format: ABC-123" in html
