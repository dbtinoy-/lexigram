"""Registry and persistence for configuration."""

from __future__ import annotations

from collections.abc import Collection
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.admin.settings.panel.nodes import AbstractConfigNode, ConfigSpec

__all__ = [
    "ConfigRegistry",
    "EnvStore",
    "MemoryStore",
    "ReadOnlyStore",
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

    async def set_many(
        self, items: dict[str, Any], tenant_id: str | None = None
    ) -> None:
        """Persist several values as one unit of work.

        The default implementation writes each key in turn and is therefore
        **not** atomic — a mid-way failure leaves earlier keys committed.
        Backends that can write transactionally must override this so a
        failed multi-key save does not half-apply.

        Args:
            items: Mapping of key to already-validated value.
            tenant_id: Optional tenant scope.
        """
        for key, value in items.items():
            await self.set(key, value, tenant_id=tenant_id)

    async def delete(self, key: str, tenant_id: str | None = None) -> None:
        """Remove one persisted value when the store supports ownership restore."""
        del key, tenant_id
        raise NotImplementedError("This settings store cannot remove values")

    async def delete_many(
        self, keys: Collection[str], tenant_id: str | None = None
    ) -> None:
        """Remove several persisted values using the store's delete primitive."""
        for key in keys:
            await self.delete(key, tenant_id=tenant_id)

    async def apply_many(
        self,
        items: dict[str, Any],
        *,
        delete_keys: Collection[str] = frozenset(),
        expected: dict[str, Any] | None = None,
        tenant_id: str | None = None,
    ) -> None:
        """Apply value writes and ownership removals as one logical operation.

        Storage adapters with transactions should override this method. The
        base implementation preserves compatibility for simple contributor
        stores, while making the non-atomic fallback explicit.
        """
        if expected is None:
            if items:
                await self.set_many(items, tenant_id=tenant_id)
        elif items:
            await self.set_many_if_unchanged(items, expected, tenant_id=tenant_id)
        if delete_keys:
            await self.delete_many(delete_keys, tenant_id=tenant_id)

    async def set_many_if_unchanged(
        self,
        items: dict[str, Any],
        expected: dict[str, Any],
        tenant_id: str | None = None,
    ) -> None:
        """Persist *items* only if stored values still match *expected*.

        Re-checking inside the write closes the window between a controller
        comparing a revision token and issuing the write. The default
        implementation cannot do that atomically and simply delegates, so a
        caller only gains the guarantee on backends that override this.

        Args:
            items: Mapping of key to already-validated value.
            expected: Mapping of key to the value observed when the form was
                rendered. Keys absent from the store are expected to be unset.
            tenant_id: Optional tenant scope.

        Raises:
            SettingsConflictError: If a backend detects a concurrent change.
        """
        del expected
        await self.set_many(items, tenant_id=tenant_id)

    async def supports_conditional_write(self) -> bool:
        """Report whether conditional writes are enforced atomically.

        Lets callers tell a genuine guarantee from the delegating default,
        rather than assuming every store closes the conflict window.
        """
        return False


class ReadOnlyStore(StoreBase):
    """Explicitly reject writes for externally-owned configuration sources."""

    async def set(self, key: str, value: Any, tenant_id: str | None = None) -> None:
        """Reject a single-key write instead of silently discarding it."""
        del key, value, tenant_id
        raise PermissionError("This configuration source is read-only")

    async def set_many(
        self, items: dict[str, Any], tenant_id: str | None = None
    ) -> None:
        """Reject a batch write before any item can be applied."""
        del items, tenant_id
        raise PermissionError("This configuration source is read-only")

    async def set_many_if_unchanged(
        self,
        items: dict[str, Any],
        expected: dict[str, Any],
        tenant_id: str | None = None,
    ) -> None:
        """Reject conditional writes as well."""
        del items, expected, tenant_id
        raise PermissionError("This configuration source is read-only")

    async def delete(self, key: str, tenant_id: str | None = None) -> None:
        """Reject ownership changes for externally-owned configuration."""
        del key, tenant_id
        raise PermissionError("This configuration source is read-only")

    async def apply_many(
        self,
        items: dict[str, Any],
        *,
        delete_keys: Collection[str] = frozenset(),
        expected: dict[str, Any] | None = None,
        tenant_id: str | None = None,
    ) -> None:
        """Reject mixed writes before applying any item."""
        del items, delete_keys, expected, tenant_id
        raise PermissionError("This configuration source is read-only")


class EnvStore(ReadOnlyStore):
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
        # Keep the original flat bucket for global callers and tests that use
        # the store without a tenant. Tenant-scoped settings use isolated
        # buckets so the development fallback has the same ownership boundary
        # as the database adapter.
        self._data: dict[str, Any] = {}
        self._tenant_data: dict[str, dict[str, Any]] = {}

    def _bucket(self, tenant_id: str | None) -> dict[str, Any]:
        """Return the global or tenant-isolated in-memory bucket."""
        if tenant_id is None:
            return self._data
        return self._tenant_data.setdefault(tenant_id, {})

    async def get(
        self, key: str, default: Any = None, tenant_id: str | None = None
    ) -> Any:
        """Retrieve a value from the in-memory store."""
        bucket = (
            self._data if tenant_id is None else self._tenant_data.get(tenant_id, {})
        )
        return bucket.get(key, default)

    async def contains(self, key: str, tenant_id: str | None = None) -> bool:
        """Return whether an explicit in-memory value exists."""
        bucket = (
            self._data if tenant_id is None else self._tenant_data.get(tenant_id, {})
        )
        return key in bucket

    async def set(self, key: str, value: Any, tenant_id: str | None = None) -> None:
        """Persist a value to the in-memory store."""
        self._bucket(tenant_id)[key] = value

    async def set_many(
        self, items: dict[str, Any], tenant_id: str | None = None
    ) -> None:
        """Apply every value at once so a partial write cannot be observed."""
        self._bucket(tenant_id).update(items)

    async def delete(self, key: str, tenant_id: str | None = None) -> None:
        """Remove an explicit value while leaving node defaults available."""
        self._bucket(tenant_id).pop(key, None)

    async def set_many_if_unchanged(
        self,
        items: dict[str, Any],
        expected: dict[str, Any],
        tenant_id: str | None = None,
    ) -> None:
        """Conditionally apply an ordinary in-memory settings save."""
        await self.apply_many(items, expected=expected, tenant_id=tenant_id)

    async def apply_many(
        self,
        items: dict[str, Any],
        *,
        delete_keys: Collection[str] = frozenset(),
        expected: dict[str, Any] | None = None,
        tenant_id: str | None = None,
    ) -> None:
        """Apply writes and removals atomically in the in-process store."""
        bucket = self._bucket(tenant_id)
        if expected:
            conflicts = sorted(
                key
                for key, value in expected.items()
                if key in bucket and bucket[key] != value
            )
            if conflicts:
                from lexigram.admin.settings.conflict import SettingsConflictError

                raise SettingsConflictError(
                    "Settings changed since the form was rendered: "
                    f"{', '.join(conflicts)}"
                )
        bucket.update(items)
        for key in delete_keys:
            bucket.pop(key, None)

    async def supports_conditional_write(self) -> bool:
        """In-memory reads and writes share one event-loop operation."""
        return True


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
        from lexigram.admin.settings.panel.notifications_spec import (
            NotificationsSpec,
        )
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
            NotificationsSpec,
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

        resolved_store_name = store_name if store_name in self._stores else "default"
        store = self._stores[resolved_store_name]
        from lexigram.admin.settings.panel.nodes import SecretNode

        store_labels = {
            "env": "Environment override",
            "db": "Database value",
            "application": "Effective application configuration",
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
                # Secret defaults are deliberately not sent to the renderer;
                # the secret field has its own presence-only treatment.
                "default": None if isinstance(node, SecretNode) else node.default,
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
        expected: dict[str, Any] | None = None,
        delete_keys: Collection[str] | None = None,
    ) -> None:
        """Save values for a spec to a store, skipping readonly nodes.

        Args:
            namespace: Configuration namespace being written.
            values: Submitted, node-validated values keyed by short name.
            store_name: Target store; falls back to ``default``.
            tenant_id: Optional tenant scope.
            expected: Values observed when the form was rendered. When given,
                the write is issued conditionally so a concurrent change is
                detected at write time rather than only before it.
            delete_keys: Short node names to remove from persistence, used by
                exact rollback when a value was previously unset.

        Raises:
            SettingsConflictError: If *expected* is supplied and the store
                detects that the stored values changed concurrently.
        """
        spec = self._specs.get(namespace)
        if not spec:
            return

        store = self._stores.get(store_name, self._stores["default"])
        nodes = spec.get_nodes()

        delete_keys = delete_keys or set()

        # Validate the whole batch before writing any of it: a value that
        # fails validation must not leave earlier keys already committed.
        pending: dict[str, Any] = {}
        for key, value in values.items():
            if key in nodes and not nodes[key].readonly:
                pending[f"{namespace}.{key}"] = nodes[key].validate(value)

        pending_deletes = {
            f"{namespace}.{key}"
            for key in delete_keys
            if key in nodes and not nodes[key].readonly
        }
        if not pending and not pending_deletes:
            return

        # Keep the established single-operation hooks for ordinary saves.
        # The combined hook below is reserved for exact rollback deletes, so
        # existing contributor stores and test doubles retain their contract.
        if not pending_deletes:
            if expected is None:
                await store.set_many(pending, tenant_id=tenant_id)
            else:
                expected_written = {
                    f"{namespace}.{key}": expected[key]
                    for key in expected
                    if key in nodes and key in values
                }
                await store.set_many_if_unchanged(
                    pending, expected_written, tenant_id=tenant_id
                )
            return

        # Only the keys being written or removed need to be unchanged.
        # Comparing the whole spec would reject saves that touch disjoint
        # fields and would make an absent expected key ambiguous.
        expected_applied = None
        if expected is not None:
            expected_applied = {
                f"{namespace}.{key}": expected[key]
                for key in set(expected).intersection(nodes)
                if key in values or key in delete_keys
            }

        applier = getattr(store, "apply_many", None)
        if callable(applier):
            await applier(
                pending,
                delete_keys=pending_deletes,
                expected=expected_applied,
                tenant_id=tenant_id,
            )
            return

        # Preserve compatibility with third-party stores that predate the
        # combined apply hook. Their fallback may not be atomic.
        if expected_applied is None:
            if pending:
                await store.set_many(pending, tenant_id=tenant_id)
        elif pending:
            await store.set_many_if_unchanged(
                pending, expected_applied, tenant_id=tenant_id
            )
        if pending_deletes:
            await store.delete_many(pending_deletes, tenant_id=tenant_id)

    async def supports_conditional_write(self, store_name: str = "default") -> bool:
        """Report whether *store_name* enforces conditional writes atomically."""
        store = self._stores.get(store_name, self._stores["default"])
        try:
            return await store.supports_conditional_write()
        except Exception:  # noqa: BLE001 — capability probes must not fail a save
            return False
