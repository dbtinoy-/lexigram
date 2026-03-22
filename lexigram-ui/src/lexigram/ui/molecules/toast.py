"""Toast notification — inline Alpine.js component and shared types.

This module provides the inline ``InlineToast`` Component (Alpine.js show/hide)
and re-exports the server-driven toast system from the layout layer
so consumers have a single import path.
"""

from __future__ import annotations

from typing import Any

from lexigram.ui.core.base import Component, el
from lexigram.ui.layouts.server_toasts import (
    ServerToastChannel,
    ToastData,
    ToastRenderer,
    ToastType,
    flash_to_toast,
)
from lexigram.ui.styles import get_semantic_icon, get_toast_classes

__all__ = [
    "InlineToast",
    "Toast",  # deprecated alias for InlineToast
    "ToastData",
    "ServerToastChannel",
    "ToastRenderer",  # deprecated alias for ServerToastChannel
    "ToastType",
    "flash_to_toast",
]


class InlineToast(Component):
    """Toast notification component with Alpine.js auto-dismiss and optional action.

    For server-driven toasts (HTMX ``X-Toast`` headers, configurable position,
    stacking), use ``ServerToastChannel`` with ``ToastData`` instead.

    Args:
        message: Notification message.
        toast_type: Severity — ``"info"``, ``"success"``, ``"warning"``, ``"error"``.
        duration: Auto-dismiss delay in milliseconds (default 3000).
        action_label: Optional label for an inline action button.
        action_url: URL the action button links to (``href`` when set).
    """

    def __init__(
        self,
        message: str,
        toast_type: str = "info",
        duration: int = 3000,
        action_label: str = "",
        action_url: str = "",
        **props: Any,
    ) -> None:
        super().__init__(
            message=message,
            type=toast_type,
            duration=duration,
            action_label=action_label,
            action_url=action_url,
            **props,
        )
        self.message = message
        self.type = toast_type
        self.duration = duration
        self.action_label = action_label
        self.action_url = action_url

    def render(self) -> Any:
        from lexigram.ui.atoms.icons import get_icon

        bg_color = get_toast_classes(self.type)
        icon_name = get_semantic_icon(self.type)

        inner: list[Any] = [
            el(
                "div",
                get_icon(icon_name, class_name="w-5 h-5"),
                class_="mr-3 flex-shrink-0",
            ),
            el("div", self.message, class_="font-medium flex-1"),
        ]

        if self.action_label:
            action_attrs: dict[str, Any] = {
                "class_": "ml-4 text-sm font-semibold underline underline-offset-2 hover:opacity-80 focus:outline-none focus:ring-2 focus:ring-offset-2 rounded",
            }
            if self.action_url:
                action_el = el(
                    "a", self.action_label, href=self.action_url, **action_attrs
                )
            else:
                action_el = el(
                    "button", self.action_label, type="button", **action_attrs
                )
            inner.append(action_el)

        inner.append(
            el(
                "button",
                "✕",
                type="button",
                aria_label="Close",
                **{
                    "class_": "ml-3 flex-shrink-0 opacity-70 hover:opacity-100 focus:outline-none",
                    "@click": "show = false",
                },
            ),
        )

        is_error = self.type in ("error", "danger")
        return el(
            "div",
            *inner,
            role="alert" if is_error else "status",
            class_=f"fixed bottom-4 right-4 {bg_color} px-4 py-3 rounded-lg shadow-lg z-50 transition-all duration-300 transform flex items-center max-w-sm",
            **{
                "x-data": "{ show: true }",
                "x-show": "show",
                "x-init": f"setTimeout(() => show = false, {self.duration})",
                "x-transition:enter": "transition ease-out duration-300",
                "x-transition:enter-start": "opacity-0 translate-y-2",
                "x-transition:enter-end": "opacity-100 translate-y-0",
                "x-transition:leave": "transition ease-in duration-200",
                "x-transition:leave-start": "opacity-100 translate-y-0",
                "x-transition:leave-end": "opacity-0 translate-y-2",
            },
            aria_live="assertive" if is_error else "polite",
        )


class Toast(InlineToast):
    """Deprecated alias for InlineToast. Will be removed in a future release."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        import warnings

        warnings.warn(
            "`Toast` (the Alpine inline-notification Component) is deprecated; "
            "use `InlineToast` instead. For the toast payload dataclass, use `ToastData`. "
            "For server-driven toasts, use `ServerToastChannel`.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)
