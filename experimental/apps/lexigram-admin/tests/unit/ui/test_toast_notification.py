"""Tests for the fluent ToastNotification builder."""

from __future__ import annotations

import pytest

from lexigram.admin.ui.molecules.toast_notification import ToastNotification
from lexigram.ui import ToastType


class TestToastNotification:
    def test_make_returns_builder(self) -> None:
        notification = ToastNotification.make("hello")
        assert isinstance(notification, ToastNotification)
        assert notification.to_toast().message == "hello"

    def test_title_and_message_chain(self) -> None:
        notification = ToastNotification.make().title("Saved").message("Done")
        toast = notification.to_toast()
        assert toast.title == "Saved"
        assert toast.message == "Done"

    def test_type_setters(self) -> None:
        assert ToastNotification.make().success().to_toast().type == ToastType.SUCCESS
        assert ToastNotification.make().error().to_toast().type == ToastType.ERROR
        assert ToastNotification.make().warning().to_toast().type == ToastType.WARNING
        assert ToastNotification.make().info().to_toast().type == ToastType.INFO

    def test_duration_enables_auto_dismiss(self) -> None:
        toast = ToastNotification.make().duration(2500).to_toast()
        assert toast.duration_ms == 2500
        assert toast.auto_dismiss is True

    def test_duration_zero_disables_auto_dismiss(self) -> None:
        toast = ToastNotification.make().duration(0).to_toast()
        assert toast.auto_dismiss is False

    def test_persistent_disables_auto_dismiss(self) -> None:
        toast = ToastNotification.make().persistent().to_toast()
        assert toast.auto_dismiss is False
        assert toast.duration_ms == 0

    def test_dismissible_flag(self) -> None:
        assert (
            ToastNotification.make().dismissible(False).to_toast().dismissible is False
        )

    def test_icon_override(self) -> None:
        toast = ToastNotification.make().icon("sparkles").to_toast()
        assert toast.icon == "sparkles"

    def test_actions_are_copied(self) -> None:
        actions = [{"label": "View", "onclick": "openReport()"}]
        toast = ToastNotification.make().actions(actions).to_toast()
        assert toast.actions == actions
        assert toast.actions is not actions

    def test_render_contains_message(self) -> None:
        html = ToastNotification.make("Export queued").info().render()
        assert 'class="toast' in html
        assert "Export queued" in html

    def test_render_persistent_has_no_auto_dismiss_attr(self) -> None:
        html = ToastNotification.make("Sticky").persistent().render()
        assert "data-auto-dismiss" not in html

    def test_render_renders_actions(self) -> None:
        html = (
            ToastNotification.make("x")
            .actions([{"label": "Go", "onclick": "go()"}])
            .render()
        )
        assert "Go" in html
        assert "go()" in html

    def test_send_flashes_full_payload(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[tuple[object, ...]] = []

        def capture(message: str, category: str, **payload: object) -> None:
            calls.append((message, category, payload))

        monkeypatch.setattr(
            "lexigram.admin.ui.molecules.toast_notification.flash",
            capture,
        )
        ToastNotification.make("Updated").success().title("Saved").duration(4000).send()
        assert len(calls) == 1
        message, category, payload = calls[0]
        assert message == "Updated"
        assert category == "success"
        assert payload["title"] == "Saved"
        assert payload["duration_ms"] == 4000
        assert payload["auto_dismiss"] is True

    def test_send_flashes_payload_without_defaults_repeated(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[tuple[object, ...]] = []

        def capture(message: str, category: str, **payload: object) -> None:
            calls.append((message, category, payload))

        monkeypatch.setattr(
            "lexigram.admin.ui.molecules.toast_notification.flash",
            capture,
        )
        ToastNotification.make("body").error().send()
        message, _category, payload = calls[0]
        assert message == "body"
        assert payload["title"] is None
        assert payload["dismissible"] is True
