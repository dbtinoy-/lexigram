from __future__ import annotations

from typing import TYPE_CHECKING, Any

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

_CREATE_SQL = f"""
CREATE TABLE IF NOT EXISTS {_TABLE} (
    tenant_id   VARCHAR(255) NOT NULL,
    key         VARCHAR(255) NOT NULL,
    value       TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, key)
)
"""


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
            await self._db.execute(_CREATE_SQL, [])
            self._initialized = True
            logger.info("Ensured %s table exists", _TABLE)
        except Exception:
            logger.exception("Failed to create %s table", _TABLE)
            raise

    async def get_config(self, tenant_id: str, key: str) -> Any | None:
        await self._ensure_table()
        result = await self._db.execute(
            f"SELECT value FROM {_TABLE} WHERE tenant_id = ? AND key = ?",
            [tenant_id, key],
        )
        if hasattr(result, "rows") and result.rows:
            raw = result.rows[0].get("value")
            return loads_str(raw) if raw is not None else None
        return None

    async def get_all_config(self, tenant_id: str) -> dict[str, Any]:
        await self._ensure_table()
        result = await self._db.execute(
            f"SELECT key, value FROM {_TABLE} WHERE tenant_id = ?",
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
            f"""INSERT INTO {_TABLE} (tenant_id, key, value)
               VALUES (?, ?, ?)
               ON CONFLICT (tenant_id, key)
               DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()""",
            [tenant_id, key, dumps_str(value)],
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

    async def set_all(self, tenant_id: str, settings: dict[str, Any]) -> None:
        if self._provider is None:
            self._memory.setdefault(tenant_id, {}).update(
                {k: v for k, v in settings.items() if k in DEFAULT_SETTINGS}
            )
            return
        for name, value in settings.items():
            if name in DEFAULT_SETTINGS:
                await self._provider.set_config(tenant_id, self._key(name), value)

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


__all__ = ["DEFAULT_SETTINGS", "AdminSettingsDbProvider", "AdminSettingsService"]
