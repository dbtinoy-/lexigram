"""Component registry for htpy components with lazy loading and versioning."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, TypeVar

from lexigram.primitives.lazy import LazyImport

T = TypeVar("T")


@dataclass
class ComponentMetadata:
    """Metadata for a registered component."""

    name: str
    component_class: type | str  # Class or import path
    version: str = "1.0.0"
    description: str = ""
    tags: list[str] = field(default_factory=list)
    registered_at: datetime = field(default_factory=datetime.now)
    lazy: bool = False
    deprecated: bool = False
    replacement: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "tags": self.tags,
            "registered_at": self.registered_at.isoformat(),
            "lazy": self.lazy,
            "deprecated": self.deprecated,
            "replacement": self.replacement,
        }


from lexigram.primitives.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable


class ComponentRegistry(Registry[str, ComponentMetadata]):
    """
    Registry for htpy components with lazy loading support.

    Provides component registration, discovery, versioning, and lazy loading
    capabilities for htpy-based UI components.
    """

    def __init__(self) -> None:
        """Initialize component registry."""
        super().__init__(name="components")
        self._aliases: dict[str, str] = {}
        self._lazy_loaders: dict[str, LazyImport] = {}

    def register(  # type: ignore[override]
        self,
        name: str,
        component_class: type,
        version: str = "1.0.0",
        description: str = "",
        tags: list[str] | None = None,
        aliases: list[str] | None = None,
    ) -> ComponentMetadata:
        """
        Register a component with the registry.
        """
        if name in self._items:
            existing = self._items[name]
            if not existing.deprecated:
                raise ValueError(
                    f"Component '{name}' already registered at version {existing.version}",
                )

        metadata = ComponentMetadata(
            name=name,
            component_class=component_class,
            version=version,
            description=description,
            tags=tags or [],
            lazy=False,
        )

        super().register(name, metadata)

        # Register aliases
        if aliases:
            for alias in aliases:
                self._aliases[alias] = name

        return metadata

    def register_lazy(
        self,
        name: str,
        import_path: str,
        version: str = "1.0.0",
        description: str = "",
        tags: list[str] | None = None,
        aliases: list[str] | None = None,
    ) -> ComponentMetadata:
        """
        Register a component for lazy loading.
        """
        if name in self._items:
            existing = self._items[name]
            if not existing.deprecated:
                raise ValueError(
                    f"Component '{name}' already registered at version {existing.version}",
                )

        # Create lazy loader
        module_path, _class_name = import_path.rsplit(".", 1)
        lazy_loader = LazyImport(module_path)

        metadata = ComponentMetadata(
            name=name,
            component_class=import_path,
            version=version,
            description=description,
            tags=tags or [],
            lazy=True,
        )

        super().register(name, metadata)
        self._lazy_loaders[name] = lazy_loader

        # Register aliases
        if aliases:
            for alias in aliases:
                self._aliases[alias] = name

        return metadata

    def get(self, name: str) -> type:  # type: ignore[override]
        """
        Get a component by name.
        """
        # Resolve alias
        if name in self._aliases:
            name = self._aliases[name]

        metadata = super().get(name)
        if metadata is None:
            raise KeyError(f"Component '{name}' not found in registry")

        # Check if deprecated
        if metadata.deprecated:
            msg = f"Component '{name}' is deprecated"
            if metadata.replacement:
                msg += f". Use '{metadata.replacement}' instead"
            raise ValueError(msg)

        # Handle lazy loading
        if metadata.lazy:
            lazy_loader = self._lazy_loaders[name]
            _module_path, class_name = str(metadata.component_class).rsplit(".", 1)
            return getattr(lazy_loader, class_name)
        return metadata.component_class  # type: ignore[return-value]

    def has(self, name: str) -> bool:
        """Check if component is registered."""
        if name in self._aliases:
            name = self._aliases[name]
        return super().has(name)

    def deprecate(
        self,
        name: str,
        replacement: str | None = None,
        message: str | None = None,
    ) -> None:
        """Mark a component as deprecated."""
        metadata = super().get(name)
        if metadata is None:
            raise KeyError(f"Component '{name}' not found")

        metadata.deprecated = True
        metadata.replacement = replacement

    def list_components(
        self,
        tags: list[str] | None = None,
        include_deprecated: bool = False,
    ) -> list[str]:
        """List all registered component names."""
        components = []

        for name, metadata in self.items():
            # Skip deprecated unless requested
            if metadata.deprecated and not include_deprecated:
                continue

            # Filter by tags
            if tags and not any(tag in metadata.tags for tag in tags):
                continue

            components.append(name)

        return sorted(components)

    def get_metadata(self, name: str) -> ComponentMetadata:
        """Get component metadata."""
        if name in self._aliases:
            name = self._aliases[name]

        metadata = super().get(name)
        if metadata is None:
            raise KeyError(f"Component '{name}' not found")

        return metadata

    def get_version(self, name: str) -> str:
        """
        Get component version.

        Args:
            name: Component name

        Returns:
            Version string
        """
        return self.get_metadata(name).version

    def check_version(self, name: str, required_version: str) -> bool:
        """
        Check if component version meets requirement.

        Simple version comparison (not full semantic versioning).

        Args:
            name: Component name
            required_version: Required version (e.g., "1.0.0")

        Returns:
            True if version matches or is newer
        """
        current = self.get_version(name)
        return self._compare_versions(current, required_version) >= 0

    def _compare_versions(self, v1: str, v2: str) -> int:
        """
        Compare two version strings.

        Args:
            v1: First version
            v2: Second version

        Returns:
            -1 if v1 < v2, 0 if equal, 1 if v1 > v2
        """
        parts1 = [int(x) for x in v1.split(".")]
        parts2 = [int(x) for x in v2.split(".")]

        # Pad to same length
        max_len = max(len(parts1), len(parts2))
        parts1.extend([0] * (max_len - len(parts1)))
        parts2.extend([0] * (max_len - len(parts2)))

        for p1, p2 in zip(parts1, parts2, strict=False):
            if p1 < p2:
                return -1
            if p1 > p2:
                return 1

        return 0

    def clear(self) -> None:
        """Clear all registered components."""
        super().clear()
        self._aliases.clear()
        self._lazy_loaders.clear()

    def export_manifest(self) -> dict[str, Any]:
        """Export registry as manifest."""
        return {
            "components": {name: metadata.to_dict() for name, metadata in self.items()},
            "aliases": self._aliases.copy(),
        }


_DEFAULT_REGISTRY: ComponentRegistry | None = None


def get_component_registry(context: Any | None = None) -> ComponentRegistry:
    """Get the component registry — from DI resolver if available, else the module singleton.

    When a resolver is present in the current admin context (e.g. inside a
    request or application scope), the registry is resolved from the DI
    container. Otherwise a module-level singleton is returned so that the
    registry is usable in tests and standalone scripts without a running
    application.
    """
    global _DEFAULT_REGISTRY

    from lexigram.admin.lib.di import get_admin_resolver

    try:
        resolver = get_admin_resolver(context)
        registry = resolver.resolve_sync(ComponentRegistry)  # type: ignore[attr-defined]
        if hasattr(registry, "__await__"):
            raise RuntimeError(
                "Resolved coroutine instead of ComponentRegistry directly",
            )
        return registry
    except RuntimeError:
        # No resolver in scope — fall back to the module-level singleton
        if _DEFAULT_REGISTRY is None:
            _DEFAULT_REGISTRY = ComponentRegistry()
        return _DEFAULT_REGISTRY


def register_component(
    name: str,
    component_class: type | None = None,
    import_path: str | None = None,
    **kwargs: Any,
) -> Callable[[type], type] | None:
    """
    Decorator to register a component.

    Can be used as a decorator or function.

    Usage:
        ```python
        # As decorator
        @register_component("button", version="1.0.0")
        class Button:
            pass

        # As function
        register_component("button", Button, version="1.0.0")

        # With lazy loading
        register_component(
            "data_table",
            import_path="lexigram.admin.ui.organisms.DataTable"
        )
        ```

    Args:
        name: Component name
        component_class: Component class (for direct registration)
        import_path: Import path (for lazy loading)
        **kwargs: Additional metadata (version, description, tags, etc.)

    Returns:
        Decorator function or None
    """
    registry = get_component_registry()

    if component_class is not None:
        # Direct registration
        registry.register(name, component_class, **kwargs)
        return None
    if import_path is not None:
        # Lazy registration
        registry.register_lazy(name, import_path, **kwargs)
        return None

    # Used as decorator
    def decorator(cls: type) -> type:
        registry.register(name, cls, **kwargs)
        return cls

    return decorator
