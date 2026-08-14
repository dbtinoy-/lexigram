"""Tests for HtmxActionResponse builder (S6)."""

from __future__ import annotations

import json


def test_toast_type_is_str_enum() -> None:
    from enum import Enum
    from lexigram.ui.htmx.action_response import ToastType

    assert issubclass(ToastType, str)
    assert issubclass(ToastType, Enum)
    assert ToastType.SUCCESS == "success"
    assert ToastType.ERROR == "error"
    assert ToastType.WARNING == "warning"
    assert ToastType.INFO == "info"


def test_to_response_returns_html_response() -> None:
    from starlette.responses import HTMLResponse

    from lexigram.ui.htmx.action_response import HtmxActionResponse, ToastData, ToastType

    resp = HtmxActionResponse(
        toast=ToastData(message="User deleted", type=ToastType.SUCCESS),
        trigger={"refresh-list": True},
    ).to_response()

    assert isinstance(resp, HTMLResponse)
    assert resp.status_code == 200
    assert resp.body == b""


def test_hx_trigger_header_is_merged() -> None:
    from lexigram.ui.htmx.action_response import HtmxActionResponse, ToastData, ToastType

    resp = HtmxActionResponse(
        toast=ToastData(message="Saved", type=ToastType.SUCCESS),
        trigger={"refresh-list": True},
    ).to_response()

    trigger_header = resp.headers.get("hx-trigger") or resp.headers.get("HX-Trigger")
    assert trigger_header is not None, "HX-Trigger header missing"
    payload = json.loads(trigger_header)
    assert payload["show-toast"]["message"] == "Saved"
    assert payload["show-toast"]["type"] == "success"
    assert payload["refresh-list"] is True


def test_trigger_only_no_extra_keys() -> None:
    from lexigram.ui.htmx.action_response import HtmxActionResponse, ToastData, ToastType

    resp = HtmxActionResponse(
        toast=ToastData(message="Done", type=ToastType.INFO),
    ).to_response()

    trigger_header = resp.headers.get("hx-trigger") or resp.headers.get("HX-Trigger")
    payload = json.loads(trigger_header)
    assert set(payload.keys()) == {"show-toast"}


def test_custom_status_code() -> None:
    from lexigram.ui.htmx.action_response import HtmxActionResponse, ToastData, ToastType

    resp = HtmxActionResponse(
        toast=ToastData(message="Oops", type=ToastType.ERROR),
        status_code=422,
    ).to_response()

    assert resp.status_code == 422


def test_no_toast_trigger_only() -> None:
    from lexigram.ui.htmx.action_response import HtmxActionResponse

    resp = HtmxActionResponse(
        trigger={"close-modal": True},
    ).to_response()

    trigger_header = resp.headers.get("hx-trigger") or resp.headers.get("HX-Trigger")
    payload = json.loads(trigger_header)
    assert payload == {"close-modal": True}
    assert "show-toast" not in payload


def test_importable_from_htmx_subpackage() -> None:
    from lexigram.ui.htmx import HtmxActionResponse, ToastData, ToastType

    assert HtmxActionResponse is not None


def test_importable_from_public_api() -> None:
    from lexigram.ui import HtmxActionResponse

    assert HtmxActionResponse is not None
