"""Registry and persistence for configuration."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.admin.settings.panel.nodes import AbstractConfigNode, ConfigSpec

__all__ = [
    "ConfigRegistry",
    "EnvStore",
    "MemoryStore",
    "StoreBase",
]


class StoreBase:
    """Interface for configuration persistence."""

    async def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value by key."""
        return default

    async def set(self, key: str, value: Any) -> None:
        """Persist a value by key."""


class EnvStore(StoreBase):
    """Read-only store for environment variables."""

    async def get(self, key: str, default: Any = None) -> Any:
        """Read a value from environment variables.

        Converts internal dot-notation keys (e.g. ``app.db.url``) to
        ``SCREAMING_SNAKE_CASE`` environment variable names.
        """
        env_key = key.upper().replace(".", "_")
        return os.environ.get(env_key, default)


class MemoryStore(StoreBase):
    """In-memory store for testing."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from the in-memory store."""
        return self._data.get(key, default)

    async def set(self, key: str, value: Any) -> None:
        """Persist a value to the in-memory store."""
        self._data[key] = value


class ConfigRegistry:
    """Central registry for specs and stores."""

    def __init__(self) -> None:
        self._specs: dict[str, type[ConfigSpec]] = {}
        self._stores: dict[str, StoreBase] = {
            "env": EnvStore(),
            "default": MemoryStore(),
        }
        self._category_map: dict[str, list[str]] = {
            "env": [],
            "app": [],
            "system": [],
        }

    def register_store(self, name: str, store: StoreBase) -> None:
        """Register a configuration store."""
        self._stores[name] = store

    def register_spec(self, category: str, spec: type[ConfigSpec]) -> None:
        """Register a spec under a category (env, admin, app)."""
        if spec.namespace in self._specs:
            return

        self._specs[spec.namespace] = spec
        if category in self._category_map:
            self._category_map[category].append(spec.namespace)

    def get_specs(self, category: str) -> list[type[ConfigSpec]]:
        """Get all registered specs for a category that have editable nodes."""
        namespaces = self._category_map.get(category, [])
        return [
            self._specs[ns]
            for ns in namespaces
            if ns in self._specs and self._specs[ns].get_nodes()
        ]

    def get_spec(self, namespace: str) -> type[ConfigSpec] | None:
        """Get a registered spec by namespace."""
        return self._specs.get(namespace)

    def has_store(self, name: str) -> bool:
        """Check whether a store is registered."""
        return name in self._stores

    @classmethod
    def with_defaults(cls) -> ConfigRegistry:
        """Build a registry pre-populated with all built-in bound specs."""
        registry = cls()
        from lexigram.admin.settings.panel import (
            register_branding_spec,
            register_cache_spec,
            register_features_spec,
            register_i18n_spec,
            register_profiler_spec,
            register_rate_limit_spec,
            register_rbac_spec,
            register_security_spec,
        )

        register_branding_spec(registry)
        register_cache_spec(registry)
        register_security_spec(registry)
        register_features_spec(registry)
        register_i18n_spec(registry)
        register_profiler_spec(registry)
        register_rate_limit_spec(registry)
        register_rbac_spec(registry)
        return registry

    def get_node(self, full_key: str) -> AbstractConfigNode | None:
        """Get a ConfigNode by its full key (namespace.key)."""
        if "." not in full_key:
            return None

        # Try to find the longest matching namespace
        for ns, spec in self._specs.items():
            if full_key.startswith(ns + "."):
                node_key = full_key[len(ns) + 1 :]
                nodes = spec.get_nodes()
                if node_key in nodes:
                    return nodes[node_key]
        return None

    async def get_values(
        self,
        namespace: str,
        store_name: str = "default",
    ) -> dict[str, Any]:
        """Load current values for a spec from a store."""
        spec = self._specs.get(namespace)
        if not spec:
            return {}

        store = self._stores.get(store_name, self._stores["default"])
        values = {}
        for key, node in spec.get_nodes().items():
            full_key = f"{namespace}.{key}"
            raw_val = await store.get(full_key, node.default)
            values[key] = node.validate(raw_val)
        return values

    async def save_values(
        self,
        namespace: str,
        values: dict[str, Any],
        store_name: str = "default",
    ) -> None:
        """Save values for a spec to a store."""
        spec = self._specs.get(namespace)
        if not spec:
            return

        store = self._stores.get(store_name, self._stores["default"])
        nodes = spec.get_nodes()
        for key, value in values.items():
            if key in nodes:
                full_key = f"{namespace}.{key}"
                validated = nodes[key].validate(value)
                await store.set(full_key, validated)
