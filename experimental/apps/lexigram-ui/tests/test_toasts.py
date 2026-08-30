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


def test_flash_to_toast_handles_struct_dicts_full_fidelity():
    """Structured flash entries must keep title/icon/duration/actions."""
    from lexigram.ui import ToastData, flash_to_toast

    toasts = flash_to_toast(
        [
            {
                "message": "Created successfully",
                "category": "success",
                "title": "Saved",
                "icon": "sparkles",
                "duration_ms": 4000,
                "dismissible": True,
                "actions": [{"label": "View", "onclick": "open()"}],
            }
        ]
    )
    assert len(toasts) == 1
    toast = toasts[0]
    assert isinstance(toast, ToastData)
    assert toast.message == "Created successfully"
    assert str(toast.type) == "success"
    assert toast.title == "Saved"
    assert toast.icon == "sparkles"
    assert toast.duration_ms == 4000
    assert toast.auto_dismiss is True
    assert toast.dismissible is True
    assert toast.actions == [{"label": "View", "onclick": "open()"}]


def test_flash_to_toast_still_accepts_legacy_tuples():
    """Legacy (category, message) tuples keep working."""
    from lexigram.ui import flash_to_toast

    toasts = flash_to_toast([("error", "Something broke")])
    assert len(toasts) == 1
    assert toasts[0].message == "Something broke"
    assert str(toasts[0].type) == "error"


def test_flash_to_toast_dict_titles_render_in_markup():
    """The full-fidelity payload must survive render_toast markup."""
    from lexigram.ui import ServerToastChannel, flash_to_toast

    toasts = flash_to_toast(
        [
            {
                "message": "Updated successfully",
                "category": "success",
                "title": "Saved",
                "icon": "check-circle",
                "duration_ms": 4000,
            }
        ]
    )
    html = ServerToastChannel().render(toasts)
    assert "Updated successfully" in html
    assert "Saved" in html
    assert "check-circle" in html
