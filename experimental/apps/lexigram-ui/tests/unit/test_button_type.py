"""Button ``type`` attribute passthrough.

``Button`` historically hard-coded ``type=\"button\"`` and silently dropped an
explicit ``type`` — which forced form implementations to fall back to inline
``onclick`` submit JavaScript.  An explicit ``type`` must now be honored so
native (and htmx-intercepted) form submission works with no JS.
"""

from __future__ import annotations

from lexigram.ui import Button, render_to_string


class TestButtonType:
    def test_submit_type_is_honored(self) -> None:
        html = render_to_string(Button("Save", type="submit"))
        assert 'type="submit"' in html
        assert 'type="button"' not in html

    def test_button_type_is_default(self) -> None:
        html = render_to_string(Button("Open"))
        assert 'type="button"' in html

    def test_outline_variant_preserves_type(self) -> None:
        html = render_to_string(Button("Cancel", variant="outline", type="submit"))
        assert 'type="submit"' in html
