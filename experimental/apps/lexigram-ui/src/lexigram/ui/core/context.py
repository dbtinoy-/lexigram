"""Per-request UI context.

Stores request-scoped rendering state (theme, locale, current user) using a
``contextvars.ContextVar`` so that async handlers running concurrently each
see their own isolated copy.

Usage — middleware::

    from lexigram.ui.core.context import UIContext, set_ui_context

    class UIContextMiddleware:
        def __init__(self, app):
            self._app = app

        async def __call__(self, scope, receive, send):
            ctx = UIContext(
                theme=scope.get("state", {}).get("theme", "default"),
                locale=scope.get("state", {}).get("locale", "en"),
            )
            token = set_ui_context(ctx)
            try:
                await self._app(scope, receive, send)
            finally:
                reset_ui_context(token)

Usage — component::

    from lexigram.ui.core.context import get_ui_context

    class ThemeAwareBadge(Component):
        def render(self):
            ctx = get_ui_context()
            theme_class = f"badge-{ctx.theme}" if ctx else "badge-default"
            return el("span", {"class": theme_class}, *self.children)
"""

from __future__ import annotations

import contextvars
import dataclasses
from typing import Any


@dataclasses.dataclass(frozen=True)
class UIContext:
    """Immutable per-request UI rendering context.

    Attributes:
        theme: Active theme name (e.g. ``"default"``, ``"dark"``).
        locale: BCP-47 locale string (e.g. ``"en"``, ``"fr-FR"``).
        user: Optional current user object; application-defined type.
        extra: Arbitrary extra key-value pairs for application-specific state.
    """

    theme: str = "default"
    locale: str = "en"
    user: Any | None = None
    extra: dict[str, Any] = dataclasses.field(default_factory=dict)

    def __repr__(self) -> str:
        user_repr = (
            getattr(self.user, "id", None) or str(self.user) if self.user else None
        )
        return (
            f"UIContext(theme={self.theme!r}, locale={self.locale!r}"
            + (f", user={user_repr!r}" if user_repr is not None else "")
            + ")"
        )


_ctx_var: contextvars.ContextVar[UIContext | None] = contextvars.ContextVar(
    "lexigram_ui_context",
    default=None,
)


def get_ui_context() -> UIContext | None:
    """Return the current request-scoped :class:`UIContext`, or ``None`` outside a request.

    Returns:
        The active :class:`UIContext` set by :func:`set_ui_context`, or ``None``
        if called outside of a request (e.g. during startup).
    """
    return _ctx_var.get()


def set_ui_context(ctx: UIContext) -> contextvars.Token[UIContext | None]:
    """Bind *ctx* as the active UI context for the current async task.

    Args:
        ctx: The :class:`UIContext` to set as active.

    Returns:
        A :class:`~contextvars.Token` that can be passed to :func:`reset_ui_context`
        to restore the previous value.
    """
    return _ctx_var.set(ctx)


def reset_ui_context(token: contextvars.Token[UIContext | None]) -> None:
    """Restore the previous UI context using the token returned by :func:`set_ui_context`.

    Args:
        token: The token returned by :func:`set_ui_context`.
    """
    _ctx_var.reset(token)


__all__ = [
    "UIContext",
    "get_ui_context",
    "reset_ui_context",
    "set_ui_context",
]
