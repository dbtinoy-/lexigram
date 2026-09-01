"""The shared live-widget EventSource must not leak or die silently.

The original script guarded on a boolean flag and registered only
``onmessage``: after an SPA body swap the flag was still truthy, so the
stream was never re-established, and a dropped connection was never
cleaned up or closed on unload.
"""

from __future__ import annotations

from lexigram.admin.dashboard.widget_cards import (
    _render_live_widget_script as live_widget_stream_script,
)


class TestLiveWidgetStreamScript:
    def test_uses_the_configured_admin_mount(self) -> None:
        script = live_widget_stream_script("/backoffice")
        assert "/backoffice/_sse/widgets" in script
        assert "/admin/_sse/widgets" not in script

    def test_defaults_to_the_standard_mount(self) -> None:
        assert "/admin/_sse/widgets" in live_widget_stream_script(None)

    def test_trailing_slash_is_normalized(self) -> None:
        assert "/backoffice/_sse/widgets" in live_widget_stream_script("/backoffice/")

    def test_guard_allows_reconnect_after_close(self) -> None:
        """A closed connection (readyState 2) must not block re-init."""
        script = live_widget_stream_script("/admin")
        assert "readyState!==2" in script
        # The handle itself is stored, not a bare boolean.
        assert "window.__lexigramLiveWidgets=es;" in script

    def test_registers_an_error_handler_that_clears_the_handle(self) -> None:
        script = live_widget_stream_script("/admin")
        assert "es.onerror=" in script
        assert "window.__lexigramLiveWidgets=null;" in script

    def test_closes_the_stream_on_unload(self) -> None:
        script = live_widget_stream_script("/admin")
        assert "pagehide" in script
        assert "es.close();" in script

    def test_still_refreshes_matching_live_widgets(self) -> None:
        script = live_widget_stream_script("/admin")
        assert "data-live-resources" in script
        assert "live-refresh" in script
