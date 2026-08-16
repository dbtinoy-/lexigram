"""Synchronous feature-flag–gated decorators.

Provides :func:`feature_flag_sync` and :func:`require_flag_sync` for
guarding synchronous functions behind a named feature flag.  Only suitable
when the backing provider has an in-memory evaluation path.
"""

from __future__ import annotations

from collections.abc import Callable
import functools
from typing import TYPE_CHECKING, Any, TypeVar

from lexigram.features.decorators._utils import _resolve_manager
from lexigram.features.exceptions import FeatureFlagDisabledError

if TYPE_CHECKING:
    from lexigram.features.manager.flag_manager import FlagManager
    from lexigram.features.types import FlagContext

F = TypeVar("F", bound=Callable[..., Any])


def feature_flag_sync(
    name: str,
    *,
    manager: FlagManager | None = None,
    fallback: Callable[..., Any] | None = None,
    context: FlagContext | None = None,
) -> Callable[[F], F]:
    """Decorate a **synchronous** function so it only runs when *name* is enabled.

    Evaluation uses :meth:`~lexigram.features.backends.base.AbstractFlagProvider.evaluate_sync`
    on the underlying provider.

    Args:
        name: Feature flag name to check.
        manager: Explicit manager; resolved via DI or a default when ``None``.
        fallback: Optional callable invoked when the flag is disabled.
        context: Optional evaluation context.

    Returns:
        A decorator for synchronous functions.
    """

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            mgr = _resolve_manager(manager)
            override = mgr.get_override_state(name)
            if override is True:
                return fn(*args, **kwargs)
            if override is False:
                if fallback is not None:
                    return fallback(*args, **kwargs)
                raise FeatureFlagDisabledError(name)
            provider = mgr.provider
            result = provider.evaluate_sync(name, context)
            if result.enabled:
                return fn(*args, **kwargs)
            if fallback is not None:
                return fallback(*args, **kwargs)
            raise FeatureFlagDisabledError(name)

        return wrapper  # type: ignore[return-value]

    return decorator


def require_flag_sync(
    name: str,
    *,
    manager: FlagManager | None = None,
    context: FlagContext | None = None,
) -> Callable[[F], F]:
    """Synchronous variant of :func:`~lexigram.features.decorators.require_flag`.

    Raises :class:`~lexigram.features.exceptions.FeatureFlagDisabledError`
    when *name* is disabled.

    Args:
        name: Feature flag name to check.
        manager: Explicit manager; resolved via DI or a default when ``None``.
        context: Optional evaluation context.

    Returns:
        A decorator for synchronous functions.
    """
    return feature_flag_sync(name, manager=manager, context=context)


__all__ = ["feature_flag_sync", "require_flag_sync"]
