"""Typed builder for HTMX action responses.

Consolidates the HX-Trigger header construction that Piccolina's action
bridge (and other handlers) build by hand.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from lexigram.serialization import dumps_str
from lexigram.ui.layouts.server_toasts import ToastData


class ToastType(str, Enum):
    """Severity levels for the ``show-toast`` HTMX event payload."""

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class HtmxActionResponse:
    """Builder for HTMX action responses with merged HX-Trigger headers.

    Args:
        toast: Optional toast notification to include in the trigger payload.
        trigger: Additional HX-Trigger events to merge alongside the toast.
        status_code: HTTP status code for the response (default 200).

    Usage::

        return HtmxActionResponse(
            toast=ToastData(message="User deleted", type=ToastType.SUCCESS),
            trigger={"refresh-list": True},
            status_code=200,
        ).to_response()
    """

    toast: ToastData | None = None
    trigger: dict[str, Any] = field(default_factory=dict)
    status_code: int = 200

    def _build_trigger(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.toast is not None:
            payload["show-toast"] = {
                "message": self.toast.message,
                "type": str(self.toast.type),
            }
        payload.update(self.trigger)
        return payload

    def to_response(self) -> Any:
        """Return a Starlette ``HTMLResponse`` with the merged HX-Trigger header.

        Returns:
            ``starlette.responses.HTMLResponse`` with empty body and
            ``HX-Trigger`` header set.
        """
        from starlette.responses import HTMLResponse

        trigger_payload = self._build_trigger()
        headers: dict[str, str] = {}
        if trigger_payload:
            headers["HX-Trigger"] = dumps_str(trigger_payload)
        return HTMLResponse("", status_code=self.status_code, headers=headers)


__all__ = ["HtmxActionResponse", "ToastData", "ToastType"]
