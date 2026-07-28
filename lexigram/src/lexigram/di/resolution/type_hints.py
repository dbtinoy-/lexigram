"""Type hint resolution for dependency injection.

Resolves constructor parameters and their type hints for automatic
dependency injection. Handles forward references, Annotated types,
and qualifier extraction.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import inspect
import sys
from typing import TYPE_CHECKING, Annotated, Any, get_args, get_origin, get_type_hints

from lexigram.di.markers import Named

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True, slots=True)
class InjectableParam:
    """A constructor parameter that can be dependency-injected."""

    name: str
    parameter: inspect.Parameter
    type_hint: type
    qualifier: Any | None = None
    has_default: bool = False

    @property
    def is_optional(self) -> bool:
        """Whether this parameter has a default value."""
        return self.has_default


class BoundedCache(OrderedDict):
    """OrderedDict-based LRU cache with bounded size."""

    def __init__(self, maxsize: int = 1024) -> None:
        super().__init__()
        self.maxsize = maxsize

    def __setitem__(self, key: Any, value: Any) -> None:
        if key in self:
            self.move_to_end(key)
        super().__setitem__(key, value)
        if len(self) > self.maxsize:
            self.popitem(last=False)

    def get_or_compute(self, key: Any, compute_fn: Callable[[Any], Any]) -> Any:
        """Get from cache or compute and store."""
        if key in self:
            self.move_to_end(key)
            return self[key]
        value = compute_fn(key)
        self[key] = value
        return value


class TypeHintResolverImpl:
    """Resolves constructor parameters for dependency injection.

    Inspects class __init__ signatures, resolves forward references,
    extracts Annotated qualifiers, and caches results with bounded cache.

    The shared cache size defaults to 2048 entries and can be configured
    via :attr:`~lexigram.di.config.models.DiConfig.type_hint_cache_size`.
    Call :meth:`configure` once at application start if a custom size is needed.
    """

    _global_cache: BoundedCache = BoundedCache(
        maxsize=2048,
    )

    @classmethod
    def configure(cls, cache_size: int) -> None:
        """Reconfigure the shared global cache.

        Must be called before the first resolution.  Replaces the cache in-place
        so that any already-stored resolver instances benefit.

        Args:
            cache_size: New maximum number of entries for the shared LRU cache.
        """
        cls._global_cache = BoundedCache(maxsize=cache_size)

    def __init__(self) -> None:
        """Initialize the resolver with the shared class-level cache."""

    def get_injectable_parameters(
        self,
        cls: type | object,
    ) -> dict[str, InjectableParam]:
        """Get injectable constructor parameters for a class.

        Returns parameters that have type hints and can be resolved
        by the DI container. Results are cached with bounded LRU.

        Args:
            cls: The class to inspect.

        Returns:
            Dict mapping parameter name to InjectableParam.
        """
        normalized_cls = self._normalize_target(cls)
        return self._global_cache.get_or_compute(normalized_cls, self._compute)

    def get_type_dependencies(self, cls: type | object) -> set[object]:
        """Get all types that cls depends on via constructor injection."""
        return {
            param.type_hint for param in self.get_injectable_parameters(cls).values()
        }

    def clear_cache(self) -> None:
        """Clear the resolution cache. Useful in testing."""
        self._global_cache.clear()

    def invalidate(self, cls: type | object) -> None:
        """Remove a specific class from the resolution cache.

        Useful when a class definition has changed at runtime (e.g. during
        hot-reload or test isolation) and cached constructor metadata is stale.

        Args:
            cls: The class whose cached resolution data should be evicted.
        """
        self._global_cache.pop(self._normalize_target(cls), None)

    def _normalize_target(self, cls: type | object) -> type:
        """Normalize instance inputs to their concrete class for introspection."""
        if inspect.isclass(cls):
            return cls
        return type(cls)

    def _compute(self, cls: type) -> dict[str, InjectableParam]:
        """Compute injectable parameters for a class."""
        try:
            sig = inspect.signature(cls.__init__)  # type: ignore[misc]
        except (ValueError, TypeError):
            return {}

        type_hints = self._resolve_hints(cls)

        params: dict[str, InjectableParam] = {}
        for name, param in sig.parameters.items():
            if name == "self":
                continue
            if param.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                continue

            raw_hint = type_hints.get(name)
            if raw_hint is None:
                continue

            base_type = raw_hint
            qualifier = None
            if get_origin(raw_hint) is Annotated:
                args = get_args(raw_hint)
                base_type = args[0]
                for metadata in args[1:]:
                    if not isinstance(metadata, str):
                        qualifier = metadata
                        break

            has_default = param.default is not inspect.Parameter.empty
            if qualifier is None and isinstance(param.default, Named):
                qualifier = param.default
                has_default = False

            params[name] = InjectableParam(
                name=name,
                parameter=param,
                type_hint=base_type,
                qualifier=qualifier,
                has_default=has_default,
            )

        return params

    def _resolve_hints(self, cls: type) -> dict[str, Any]:
        """Resolve type hints for cls.__init__ with namespace handling."""
        try:
            module = sys.modules.get(cls.__module__)
            globalns = getattr(module, "__dict__", None)
            return get_type_hints(
                cls.__init__,  # type: ignore[misc]
                globalns=globalns,
                localns=dict(cls.__dict__),
                include_extras=True,
            )
        except (TypeError, ValueError, KeyError, NameError):
            return {}


__all__ = ["BoundedCache", "InjectableParam", "TypeHintResolverImpl"]
