"""Decorators for UI components — metadata tagging for registry and render pipeline."""

from __future__ import annotations

from collections.abc import Callable
import functools
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

__all__ = [
    "component",
]


def component(
    name: str | None = None,
    *,
    cacheable: bool = False,
) -> Callable[[F], F]:
    """Mark a callable as a named UI component and attach component metadata.

    Tags the decorated function with ``__component_name__`` and
    ``__component_cacheable__`` attributes so that component registries,
    debug tooling, and render pipelines can discover and identify components
    by name without relying on ``__qualname__``.

    This decorator does **not** register the component in any global registry
    by itself — registration is handled by the DI container via the
    :class:`~lexigram.ui.di.provider.UIProvider`. The decorator provides
    the metadata that the provider reads during component discovery.

    Args:
        name: Logical component name used for registration and cache keys.
            Defaults to the decorated function's ``__name__``.
        cacheable: When ``True``, signals that the component's rendered output
            may be cached by the render pipeline. Defaults to ``False``.

    Returns:
        Decorator that attaches component metadata to the target callable.

    Example::

        @component("user_card", cacheable=True)
        def user_card(user: User) -> str:
            return render_to_string(
                el("div", {"class": "card"}, user.display_name)
            )

        @component()
        def avatar(src: str, alt: str = "") -> str:
            return render_to_string(el("img", {"src": src, "alt": alt}))
    """

    def decorator(fn: F) -> F:
        component_name = name or fn.__name__

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return fn(*args, **kwargs)

        wrapper.__component_name__ = component_name  # type: ignore[attr-defined]
        wrapper.__component_cacheable__ = cacheable  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator
