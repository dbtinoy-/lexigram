from __future__ import annotations

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

    def _upsert_sql(self) -> str:
        """Return the single-row upsert statement for the configured dialect."""
        return f"""INSERT INTO {_TABLE} (tenant_id, key, value)
               VALUES (?, ?, ?)
               ON CONFLICT (tenant_id, key)
               DO UPDATE SET value = excluded.value, updated_at = {now_expr(self._db)}"""  # noqa: S608 — table name is module constant, now_expr yields fixed NOW()/CURRENT_TIMESTAMP

    async def set_config_many(self, tenant_id: str, items: dict[str, Any]) -> None:
        """Upsert several config rows inside one transaction when supported.

        Falls back to sequential writes only when the database provider does
        not expose a usable ``transaction()`` context manager.

        Args:
            tenant_id: Tenant scope for every row.
            items: Mapping of fully-qualified key to value.
        """
        if not items:
            return
        await self._ensure_table()
        sql = self._upsert_sql()
        params = [[tenant_id, key, dumps_str(value)] for key, value in items.items()]

        transaction = getattr(self._db, "transaction", None)
        if callable(transaction):
            async with transaction():
                for row in params:
                    await self._db.execute(sql, row)
            return

        logger.warning(
            "Database provider exposes no transaction(); "
            "settings batch write is not atomic"
        )
        for row in params:
            await self._db.execute(sql, row)

    async def set_config_many_if_unchanged(
        self,
        tenant_id: str,
        items: dict[str, Any],
        expected: dict[str, Any],
    ) -> None:
        """Upsert rows only if their stored values still match *expected*.

        The comparison is re-executed inside the write transaction, so a
        concurrent update committed after the caller rendered its form is
        detected here rather than being silently overwritten. Raising rolls
        the transaction back, leaving no partial write behind.

        Args:
            tenant_id: Tenant scope for every row.
            items: Mapping of fully-qualified key to value.
            expected: Mapping of key to the value observed at render time. A
                key mapped to ``None`` is expected to be absent from storage.

        Raises:
            SettingsConflictError: If any row changed concurrently.
        """
        if not items:
            return
        await self._ensure_table()

        transaction = getattr(self._db, "transaction", None)
        if not callable(transaction):
            logger.warning(
                "Database provider exposes no transaction(); settings "
                "conditional write cannot be enforced atomically"
            )
            await self._verify_unchanged(tenant_id, expected)
            await self.set_config_many(tenant_id, items)
            return

        sql = self._upsert_sql()
        async with transaction():
            await self._verify_unchanged(tenant_id, expected)
            for key, value in items.items():
                await self._db.execute(sql, [tenant_id, key, dumps_str(value)])

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
        # rendered was the node default and no concurrent write can have
        # occurred. Only stored rows can conflict. This settings surface has
        # no delete path, so an absent row cannot mean "removed since read".
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
        if self._provider is None:
            return self._memory.get(tenant_id, {}).get(name) or DEFAULT_SETTINGS.get(
                name
            )
        raw = await self._provider.get_config(tenant_id, self._key(name))
        if raw is not None:
            return raw
        return DEFAULT_SETTINGS.get(name)

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
