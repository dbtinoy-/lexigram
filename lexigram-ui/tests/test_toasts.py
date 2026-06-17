from __future__ import annotations

import warnings

import pytest


def test_inline_toast_is_alpine_component():
    """InlineToast should be the Alpine-driven inline notification component."""
    from lexigram.ui import InlineToast

    t = InlineToast(message="hello", toast_type="info", duration=2000)
    html = str(t)
    assert "x-data" in html
    assert "setTimeout" in html
    assert "hello" in html


def test_server_toast_channel_renders_x_toast_payload():
    """ServerToastChannel should produce server-driven toast HTML."""
    from lexigram.ui import ServerToastChannel, ToastData

    channel = ServerToastChannel()
    payload = ToastData(message="ok", type="success")
    rendered = channel.render([payload])
    assert "ok" in rendered


def test_legacy_toast_alias_emits_deprecation_warning():
    """Importing `Toast` should still work but emit DeprecationWarning."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        from lexigram.ui import Toast  # noqa: F401

        _ = Toast(message="legacy")
    assert any(
        issubclass(w.category, DeprecationWarning)
        and "InlineToast" in str(w.message)
        for w in caught
    ), "Expected DeprecationWarning pointing at InlineToast"


def test_legacy_toast_renderer_alias_emits_deprecation_warning():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        from lexigram.ui import ToastRenderer

        _ = ToastRenderer()
    assert any(
        issubclass(w.category, DeprecationWarning)
        and "ServerToastChannel" in str(w.message)
        for w in caught
    ), "Expected DeprecationWarning pointing at ServerToastChannel"


def test_close_toast_event_listener_rendered():
    """The toast script should listen for the lexigram:close-toast event."""
    from lexigram.ui import ServerToastChannel, ToastConfig

    channel = ServerToastChannel(config=ToastConfig(listen_for_events=True))
    html = channel.render_container([])
    assert "lexigram:close-toast" in html
    assert "dismissToast" in html
    assert "evt.detail.id" in html


def test_close_toast_event_absent_when_disabled():
    """No toast script (and thus no event listener) when events are off."""
    from lexigram.ui import ServerToastChannel, ToastConfig

    channel = ServerToastChannel(config=ToastConfig(listen_for_events=False))
    html = channel.render_container([])
    assert "lexigram:close-toast" not in html
