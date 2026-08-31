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

    async def get(
        self, key: str, default: Any = None, tenant_id: str | None = None
    ) -> Any:
        """Retrieve a value by key."""
        return default

    async def contains(self, key: str, tenant_id: str | None = None) -> bool | None:
        """Report whether a store has an explicit value for ``key``.

        ``None`` means the adapter cannot determine presence. That distinction
        prevents the settings UI from incorrectly labelling an opaque external
        store's value as an application default.
        """
        return None

    async def set(self, key: str, value: Any, tenant_id: str | None = None) -> None:
        """Persist a value by key."""


class EnvStore(StoreBase):
    """Read-only store for environment variables."""

    async def get(
        self, key: str, default: Any = None, tenant_id: str | None = None
    ) -> Any:
        """Read a value from environment variables.

        Converts internal dot-notation keys (e.g. ``app.db.url``) to
        ``SCREAMING_SNAKE_CASE`` environment variable names.
        """
        env_key = key.upper().replace(".", "_")
        return os.environ.get(env_key, default)

    async def contains(self, key: str, tenant_id: str | None = None) -> bool:
        """Return whether the corresponding environment variable is set."""
        return key.upper().replace(".", "_") in os.environ


class MemoryStore(StoreBase):
    """In-memory store for testing."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def get(
        self, key: str, default: Any = None, tenant_id: str | None = None
    ) -> Any:
        """Retrieve a value from the in-memory store."""
        return self._data.get(key, default)

    async def contains(self, key: str, tenant_id: str | None = None) -> bool:
        """Return whether an explicit in-memory value exists."""
        return key in self._data

    async def set(self, key: str, value: Any, tenant_id: str | None = None) -> None:
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

    def register_store(self, name: str, store: StoreBase) -> None:
        """Register a configuration store."""
        self._stores[name] = store

    def register_spec(self, spec: type[ConfigSpec]) -> None:
        """Register a spec, grouped in the sidebar under its ``package_source``."""
        if spec.namespace in self._specs:
            return
        self._specs[spec.namespace] = spec

    def get_package_sources(self) -> list[str]:
        """Return distinct package sources among specs with editable nodes, sorted."""
        return sorted(
            {spec.package_source for spec in self._specs.values() if spec.get_nodes()}
        )

    def get_specs_by_package(self, package_source: str) -> list[type[ConfigSpec]]:
        """Get all registered specs for a package source that have editable nodes."""
        return [
            spec
            for spec in self._specs.values()
            if spec.package_source == package_source and spec.get_nodes()
        ]

    def get_spec(self, namespace: str) -> type[ConfigSpec] | None:
        """Get a registered spec by namespace."""
        return self._specs.get(namespace)

    def has_store(self, name: str) -> bool:
        """Check whether a store is registered."""
        return name in self._stores

    @classmethod
    def _default_entries(cls) -> dict[str, type[ConfigSpec]]:
        """Declare the built-in config specs keyed by namespace."""
        from lexigram.admin.settings.panel.branding_spec import BrandingSpec
        from lexigram.admin.settings.panel.cache_spec import CacheSpec
        from lexigram.admin.settings.panel.deployment_spec import DeploymentInfoSpec
        from lexigram.admin.settings.panel.features_spec import FeaturesSpec
        from lexigram.admin.settings.panel.i18n_spec import I18nSpec
        from lexigram.admin.settings.panel.profiler_spec import ProfilerSpec
        from lexigram.admin.settings.panel.rate_limit_spec import RateLimitSpec
        from lexigram.admin.settings.panel.rbac_spec import RBACSpec
        from lexigram.admin.settings.panel.security_spec import SecuritySpec

        specs: dict[str, type[ConfigSpec]] = {}
        for spec in (
            BrandingSpec,
            CacheSpec,
            DeploymentInfoSpec,
            FeaturesSpec,
            I18nSpec,
            ProfilerSpec,
            RateLimitSpec,
            RBACSpec,
            SecuritySpec,
        ):
            specs[spec.namespace] = spec
        return specs

    @classmethod
    def with_defaults(cls) -> ConfigRegistry:
        """Build a registry pre-populated with all built-in bound specs."""
        registry = cls()
        for spec in cls._default_entries().values():
            registry.register_spec(spec)
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
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Load current values for a spec from a store."""
        spec = self._specs.get(namespace)
        if not spec:
            return {}

        store = self._stores.get(store_name, self._stores["default"])
        values = {}
        for key, node in spec.get_nodes().items():
            full_key = f"{namespace}.{key}"
            raw_val = await store.get(full_key, node.default, tenant_id=tenant_id)
            # Deployment metadata historically used the namespaced key (for
            # example ADMIN_DEPLOYMENT_ENVIRONMENT). Also honour an explicit
            # environment name so standard ENVIRONMENT/LOG_LEVEL variables
            # work without breaking existing deployments.
            env_name = getattr(node, "extra", {}).get("env_name")
            if store_name == "env" and env_name:
                raw_val = await store.get(
                    env_name,
                    raw_val,
                    tenant_id=tenant_id,
                )
            values[key] = node.validate(raw_val)
        return values

    async def get_value_metadata(
        self,
        namespace: str,
        store_name: str = "default",
        tenant_id: str | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Return effective-value source metadata for a configuration spec.

        Stores that support presence checks distinguish an explicit override
        from the node default. Opaque external stores return ``None`` for
        ``configured`` rather than making the UI claim that a value is a
        default. The metadata is presentation-only; writes still go through
        ``save_values`` and server-side permissions.
        """
        spec = self._specs.get(namespace)
        if not spec:
            return {}

        resolved_store_name = (
            store_name if store_name in self._stores else "default"
        )
        store = self._stores[resolved_store_name]
        store_labels = {
            "env": "Environment override",
            "db": "Database value",
            "default": "Application setting",
        }
        configured_label = store_labels.get(
            resolved_store_name,
            resolved_store_name.replace("_", " ").title(),
        )
        metadata: dict[str, dict[str, Any]] = {}
        for key, node in spec.get_nodes().items():
            full_key = f"{namespace}.{key}"
            lookup_key = (
                getattr(node, "extra", {}).get("env_name") or full_key
                if resolved_store_name == "env"
                else full_key
            )
            try:
                configured = await store.contains(lookup_key, tenant_id=tenant_id)
            except Exception:  # noqa: BLE001 — metadata must not block rendering
                configured = None

            if configured is True:
                source = "configured"
                source_label = configured_label
            elif configured is False:
                source = "default"
                source_label = "Application default"
            else:
                source = "unknown"
                source_label = "External store value"

            metadata[key] = {
                "configured": configured,
                "is_default": configured is False,
                "source": source,
                "source_label": source_label,
                "scope": spec.scope,
                "store_name": resolved_store_name,
                "runtime_status": spec.runtime_status,
            }
        return metadata

    async def save_values(
        self,
        namespace: str,
        values: dict[str, Any],
        store_name: str = "default",
        tenant_id: str | None = None,
    ) -> None:
        """Save values for a spec to a store, skipping readonly nodes."""
        spec = self._specs.get(namespace)
        if not spec:
            return

        store = self._stores.get(store_name, self._stores["default"])
        nodes = spec.get_nodes()
        for key, value in values.items():
            if key in nodes and not nodes[key].readonly:
                full_key = f"{namespace}.{key}"
                validated = nodes[key].validate(value)
                await store.set(full_key, validated, tenant_id=tenant_id)
