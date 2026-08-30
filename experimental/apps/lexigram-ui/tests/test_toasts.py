from __future__ import annotations


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
