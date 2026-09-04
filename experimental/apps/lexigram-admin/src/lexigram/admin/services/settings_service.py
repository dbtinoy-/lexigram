from __future__ import annotations

from collections.abc import Collection
from typing import TYPE_CHECKING, Any

from lexigram.admin.settings.conflict import SettingsConflictError
from lexigram.admin.sql_dialect import is_postgres, now_expr
from lexigram.contracts.tenancy.protocols import TenantConfigProviderProtocol
from lexigram.logging import get_logger
from lexigram.serialization import dumps_str, loads_str

if TYPE_CHECKING:
    from lexigram.contracts.data import DatabaseProviderProtocol

logger = get_logger(__name__)

KEY_PREFIX = "admin_ui."

DEFAULT_SETTINGS: dict[str, Any] = {
    "site_name": "Lexigram Admin",
    "primary_color": "#6b7280",
    "logo_url": "",
    "favicon_url": "",
    "dark_mode": "system",
}


_TABLE = "tenant_configs"

_CREATE_SQL_POSTGRES = f"""
CREATE TABLE IF NOT EXISTS {_TABLE} (
    tenant_id   VARCHAR(255) NOT NULL,
    key         VARCHAR(255) NOT NULL,
    value       TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, key)
)
"""

_CREATE_SQL_SQLITE = f"""
CREATE TABLE IF NOT EXISTS {_TABLE} (
    tenant_id   VARCHAR(255) NOT NULL,
    key         VARCHAR(255) NOT NULL,
    value       TEXT NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (tenant_id, key)
)
"""


def _normalize_config_value(value: Any) -> str:
    """Return a comparable form of a stored or rendered config value.

    Values make a round trip through form encoding and JSON storage, so a
    boolean can come back as ``True`` from the database but ``"true"`` from
    the form. Comparing raw objects would report spurious conflicts, so
    everything is reduced to a canonical lower-cased string.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip().lower()


class AdminSettingsDbProvider(TenantConfigProviderProtocol):
    """DB-backed tenant config provider that auto-creates its table.

    Follows the pattern used by other lexigram packages (admin sessions,
    resilience idempotency, etc.) — creates ``tenant_configs`` on first
    use via ``CREATE TABLE IF NOT EXISTS``.
    """

    def __init__(self, db: DatabaseProviderProtocol) -> None:
        self._db = db
        self._initialized = False

    async def _ensure_table(self) -> None:
        if self._initialized:
            return
        try:
            create_sql = (
                _CREATE_SQL_POSTGRES if is_postgres(self._db) else _CREATE_SQL_SQLITE
            )
            await self._db.execute(create_sql, [])
            self._initialized = True
            logger.info("Ensured %s table exists", _TABLE)
        except Exception:
            logger.exception("Failed to create %s table", _TABLE)
            raise

    async def get_config(self, tenant_id: str, key: str) -> Any | None:
        await self._ensure_table()
        result = await self._db.execute(
            f"SELECT value FROM {_TABLE} WHERE tenant_id = ? AND key = ?",  # noqa: S608 — table name is module constant "tenant_configs", never user input
            [tenant_id, key],
        )
        if hasattr(result, "rows") and result.rows:
            raw = result.rows[0].get("value")
            return loads_str(raw) if raw is not None else None
        return None

    async def get_all_config(self, tenant_id: str) -> dict[str, Any]:
        await self._ensure_table()
        result = await self._db.execute(
            f"SELECT key, value FROM {_TABLE} WHERE tenant_id = ?",  # noqa: S608 — table name is module constant "tenant_configs", never user input
            [tenant_id],
        )
        rows: dict[str, Any] = {}
        for row in getattr(result, "rows", []) or []:
            k = row.get("key")
            v = row.get("value")
            if k is not None and v is not None:
                rows[k] = loads_str(v)
        return rows

    async def set_config(self, tenant_id: str, key: str, value: Any) -> None:
        await self._ensure_table()
        await self._db.execute(
            self._upsert_sql(),
            [tenant_id, key, dumps_str(value)],
        )

    async def delete_config(self, tenant_id: str, key: str) -> None:
        """Remove one explicit tenant setting, leaving model defaults intact."""
        await self._ensure_table()
        await self._db.execute(
            f"DELETE FROM {_TABLE} WHERE tenant_id = ? AND key = ?",  # noqa: S608 — table constant
            [tenant_id, key],
        )

    def _upsert_sql(self) -> str:
        """Return the single-row upsert statement for the configured dialect."""
        return f"""INSERT INTO {_TABLE} (tenant_id, key, value)
               VALUES (?, ?, ?)
               ON CONFLICT (tenant_id, key)
               DO UPDATE SET value = excluded.value, updated_at = {now_expr(self._db)}"""  # noqa: S608 — table name is module constant, now_expr yields fixed NOW()/CURRENT_TIMESTAMP

    async def set_config_many(self, tenant_id: str, items: dict[str, Any]) -> None:
        """Upsert several config rows inside one transaction when supported."""
        await self.apply_config_many(tenant_id, items)

    async def delete_config_many(self, tenant_id: str, keys: Collection[str]) -> None:
        """Remove several explicit config rows inside one transaction when supported."""
        await self.apply_config_many(tenant_id, {}, delete_keys=keys)

    async def apply_config_many(
        self,
        tenant_id: str,
        items: dict[str, Any],
        delete_keys: Collection[str] = frozenset(),
        expected: dict[str, Any] | None = None,
    ) -> None:
        """Apply writes and removals with one conditional transaction.

        ``delete_keys`` is used by exact rollback to restore values that were
        previously inherited from model defaults. When a provider exposes no
        transaction context, the method keeps the pre-existing best-effort
        fallback but logs that the combined operation is not atomic.
        """
        if not items and not delete_keys:
            return
        await self._ensure_table()
        upsert_sql = self._upsert_sql()
        delete_sql = f"DELETE FROM {_TABLE} WHERE tenant_id = ? AND key = ?"  # noqa: S608 — table constant

        async def _mutate() -> None:
            if expected is not None:
                await self._verify_unchanged(tenant_id, expected)
            for key, value in items.items():
                await self._db.execute(
                    upsert_sql,
                    [tenant_id, key, dumps_str(value)],
                )
            for key in delete_keys:
                await self._db.execute(delete_sql, [tenant_id, key])

        transaction = getattr(self._db, "transaction", None)
        if callable(transaction):
            async with transaction():
                await _mutate()
            return

        logger.warning(
            "Database provider exposes no transaction(); "
            "settings combined write is not atomic"
        )
        await _mutate()

    def supports_conditional_write(self) -> bool:
        """Report whether the database provider can close the race atomically."""
        return callable(getattr(self._db, "transaction", None))

    async def set_config_many_if_unchanged(
        self,
        tenant_id: str,
        items: dict[str, Any],
        expected: dict[str, Any],
    ) -> None:
        """Compatibility wrapper for the original conditional-write API."""
        await self.apply_config_many(tenant_id, items, expected=expected)

    async def _verify_unchanged(self, tenant_id: str, expected: dict[str, Any]) -> None:
        """Raise if stored values diverge from *expected*.

        Args:
            tenant_id: Tenant scope to read.
            expected: Mapping of key to the value observed at render time.

        Raises:
            SettingsConflictError: Listing the keys that changed.
        """
        if not expected:
            return
        current = await self.get_all_config(tenant_id)
        # A key absent from storage was never written, so the value the form
        # rendered was the node default and no conflicting write can be
        # inferred. A stored row with a different value is always a conflict;
        # this also protects rollback deletes from removing a later override.
        conflicts = sorted(
            key
            for key, value in expected.items()
            if key in current
            and _normalize_config_value(current[key]) != _normalize_config_value(value)
        )
        if conflicts:
            raise SettingsConflictError(
                f"Settings changed since the form was rendered: {', '.join(conflicts)}"
            )


class AdminSettingsService:
    def __init__(
        self,
        config_provider: TenantConfigProviderProtocol | None = None,
    ) -> None:
        self._provider = config_provider
        self._memory: dict[str, dict[str, Any]] = {}

    def _key(self, name: str) -> str:
        return f"{KEY_PREFIX}{name}"

    async def get(self, tenant_id: str, name: str) -> Any:
        """Read a setting while preserving explicitly stored falsy values.

        ``dict.get(...) or default`` is incorrect for configuration: ``False``,
        ``0``, and ``""`` can all be intentional operator choices. Presence
        is checked separately so only an absent value falls back to the
        application default.
        """
        if self._provider is None:
            tenant_values = self._memory.get(tenant_id, {})
            if name in tenant_values:
                return tenant_values[name]
            return DEFAULT_SETTINGS.get(name)
        raw = await self._provider.get_config(tenant_id, self._key(name))
        if raw is not None:
            return raw
        return DEFAULT_SETTINGS.get(name)

    async def contains(self, tenant_id: str, name: str) -> bool | None:
        """Report whether a tenant has an explicit stored setting.

        ``None`` is reserved for providers that cannot prove presence. The
        built-in provider can inspect its tenant row set, which lets the
        settings UI distinguish an explicit ``false`` from a default ``true``.
        """
        if self._provider is None:
            return name in self._memory.get(tenant_id, {})
        try:
            values = await self._provider.get_all_config(tenant_id)
            return self._key(name) in values if isinstance(values, dict) else None
        except Exception:
            return None

    async def get_setting(
        self,
        name: str,
        default: Any = None,
        *,
        tenant_id: str = "default",
    ) -> Any:
        """Read a runtime setting using the key/default calling convention.

        Middleware integrations historically accepted ``get(name, default)``
        while :class:`AdminSettingsService` is tenant-oriented
        (``get(tenant_id, name)``). This explicit adapter keeps both contracts
        correct and makes the runtime call site self-documenting.
        """
        value = await self.get(tenant_id, name)
        return default if value is None else value

    async def set(self, tenant_id: str, name: str, value: Any) -> None:
        if self._provider is None:
            self._memory.setdefault(tenant_id, {})[name] = value
            return
        await self._provider.set_config(tenant_id, self._key(name), value)

    async def get_all(self, tenant_id: str) -> dict[str, Any]:
        merged = dict(DEFAULT_SETTINGS)
        if self._provider is not None:
            raw = await self._provider.get_all_config(tenant_id)
            for k, v in raw.items():
                if k.startswith(KEY_PREFIX):
                    merged[k[len(KEY_PREFIX) :]] = v
        else:
            tenant_data = self._memory.get(tenant_id, {})
            merged.update(tenant_data)
        return merged

    async def set_many(self, tenant_id: str, items: dict[str, Any]) -> None:
        """Persist several named settings as one unit of work.

        Args:
            tenant_id: Tenant scope.
            items: Mapping of setting name to value.
        """
        if not items:
            return
        if self._provider is None:
            self._memory.setdefault(tenant_id, {}).update(items)
            return

        keyed = {self._key(name): value for name, value in items.items()}
        batch = getattr(self._provider, "set_config_many", None)
        if callable(batch):
            await batch(tenant_id, keyed)
            return
        for key, value in keyed.items():
            await self._provider.set_config(tenant_id, key, value)

    async def delete(self, tenant_id: str, name: str) -> None:
        """Remove an explicit setting while preserving its declared default."""
        if self._provider is None:
            self._memory.get(tenant_id, {}).pop(name, None)
            return
        delete = getattr(self._provider, "delete_config", None)
        if callable(delete):
            await delete(tenant_id, self._key(name))
            return
        logger.warning(
            "Tenant config provider does not support deletion; "
            "settings ownership cannot be restored exactly"
        )

    async def apply_many_if_unchanged(
        self,
        tenant_id: str,
        items: dict[str, Any],
        delete_names: Collection[str] = frozenset(),
        expected: dict[str, Any] | None = None,
    ) -> None:
        """Apply value writes and explicit-key removals as one logical save."""
        if not items and not delete_names:
            return

        if self._provider is None:
            stored = self._memory.setdefault(tenant_id, {})
            if expected:
                conflicts = sorted(
                    name
                    for name, value in expected.items()
                    if name in stored
                    and _normalize_config_value(stored[name])
                    != _normalize_config_value(value)
                )
                if conflicts:
                    raise SettingsConflictError(
                        "Settings changed since the form was rendered: "
                        f"{', '.join(conflicts)}"
                    )
            stored.update(items)
            for name in delete_names:
                stored.pop(name, None)
            return

        keyed = {self._key(name): value for name, value in items.items()}
        keyed_delete = {self._key(name) for name in delete_names}
        keyed_expected = (
            {self._key(name): value for name, value in expected.items()}
            if expected is not None
            else None
        )
        conditional = getattr(self._provider, "apply_config_many", None)
        if callable(conditional):
            await conditional(
                tenant_id,
                keyed,
                keyed_delete,
                keyed_expected,
            )
            return

        # Providers predating combined writes retain the old conditional
        # behavior for value updates and perform removals afterward.
        if keyed:
            if keyed_expected is None:
                await self.set_many(tenant_id, items)
            else:
                await self.set_many_if_unchanged(tenant_id, items, expected or {})
        for name in delete_names:
            await self.delete(tenant_id, name)

    async def set_many_if_unchanged(
        self,
        tenant_id: str,
        items: dict[str, Any],
        expected: dict[str, Any],
    ) -> None:
        """Persist several settings only if they have not changed concurrently.

        Args:
            tenant_id: Tenant scope.
            items: Mapping of setting name to value.
            expected: Mapping of setting name to the value read at render time.

        Raises:
            SettingsConflictError: If a concurrent change is detected.
        """
        if not items:
            return

        keyed = {self._key(name): value for name, value in items.items()}
        keyed_expected = {self._key(name): value for name, value in expected.items()}

        if self._provider is None:
            stored = self._memory.setdefault(tenant_id, {})
            conflicts = sorted(
                name
                for name, value in expected.items()
                if name in stored
                and _normalize_config_value(stored[name])
                != _normalize_config_value(value)
            )
            if conflicts:
                raise SettingsConflictError(
                    "Settings changed since the form was rendered: "
                    f"{', '.join(conflicts)}"
                )
            stored.update(items)
            return

        conditional = getattr(self._provider, "set_config_many_if_unchanged", None)
        if callable(conditional):
            await conditional(tenant_id, keyed, keyed_expected)
            return

        # Provider predates conditional writes. Fall back to a plain batch
        # rather than failing the save; the caller's pre-write revision check
        # still applies, only the residual race stays open.
        logger.warning(
            "Tenant config provider does not support conditional writes; "
            "settings save falls back to last-write-wins"
        )
        await self.set_many(tenant_id, items)

    def supports_conditional_write(self) -> bool:
        """Report whether the backing provider enforces conditional writes."""
        if self._provider is None:
            return True
        probe = getattr(self._provider, "supports_conditional_write", None)
        if callable(probe):
            try:
                return bool(probe())
            except Exception:  # noqa: BLE001 — capability is best-effort
                return False
        return callable(getattr(self._provider, "set_config_many_if_unchanged", None))

    async def set_all(self, tenant_id: str, settings: dict[str, Any]) -> None:
        known = {k: v for k, v in settings.items() if k in DEFAULT_SETTINGS}
        if self._provider is None:
            self._memory.setdefault(tenant_id, {}).update(known)
            return
        await self.set_many(tenant_id, known)

    async def get_widget_prefs(self, tenant_id: str, user_id: str) -> dict[str, Any]:
        key = f"widgets.{user_id}"
        if self._provider is None:
            data = self._memory.get(tenant_id, {}).get(key)
            return data if isinstance(data, dict) else {}
        raw = await self._provider.get_config(tenant_id, self._key(key))
        return raw if isinstance(raw, dict) else {}

    async def set_widget_prefs(
        self, tenant_id: str, user_id: str, prefs: dict[str, Any]
    ) -> None:
        key = f"widgets.{user_id}"
        if self._provider is None:
            self._memory.setdefault(tenant_id, {})[key] = prefs
            return
        await self._provider.set_config(tenant_id, self._key(key), prefs)


async def resolve_admin_settings_service(
    container: Any,
) -> AdminSettingsService | None:
    """Build a DB-backed settings service from a DI container.

    Mirrors the bundle's own construction: resolves the database provider
    and wires an :class:`AdminSettingsDbProvider` underneath.  Returns
    ``None`` when the database provider is unavailable, so callers can
    fall back to client-side defaults.

    Args:
        container: DI resolver (``ContainerResolverProtocol``).

    Returns:
        An ``AdminSettingsService`` or ``None`` if it cannot be built.
    """
    try:
        from lexigram.contracts.data import DatabaseProviderProtocol

        try:
            db_provider = await container.resolve(
                DatabaseProviderProtocol,
                bypass_visibility=True,
            )
        except TypeError:
            db_provider = await container.resolve(DatabaseProviderProtocol)
        return AdminSettingsService(
            config_provider=AdminSettingsDbProvider(db=db_provider)
        )
    except Exception as exc:  # noqa: BLE001 — non-fatal
        logger.exception(
            "admin.settings_service_resolve_failed",
            error=str(exc)[:300],
        )
        return None


__all__ = [
    "DEFAULT_SETTINGS",
    "AdminSettingsDbProvider",
    "AdminSettingsService",
    "resolve_admin_settings_service",
]
