"""SQL-backed tenant provider (optional extra).

Available when ``lexigram-tenancy[sql]`` is installed.
Raises ``ImportError`` if ``lexigram-sql`` is not available.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from lexigram.contracts.tenancy.commands import CreateTenantCommand, UpdateTenantCommand
from lexigram.contracts.tenancy.errors import TenantError, TenantNotFoundError
from lexigram.contracts.tenancy.types import TenantInfo, TenantStatus
from lexigram.result import Err, Ok, Result
import lexigram.serialization as json

if TYPE_CHECKING:
    from lexigram.contracts.data import DatabaseProviderProtocol


class SQLTenantProvider:
    """SQL-backed tenant store using the ``lexigram-sql`` repository pattern.

    Requires ``lexigram-tenancy[sql]`` and a ``tenants`` table with columns:
    ``tenant_id``, ``slug``, ``name``, ``status``, ``plan``,
    ``config`` (JSON), ``metadata`` (JSON), ``created_at``.

    Also provides config storage via a ``tenant_configs`` table with columns:
    ``tenant_id``, ``key``, ``value`` (JSON).
    """

    def __init__(self, db: DatabaseProviderProtocol) -> None:
        """Initialise the provider.

        Args:
            db: Database provider implementing
                :class:`~lexigram.contracts.data.DatabaseProviderProtocol`.
        """
        self._db = db

    async def get_tenant(self, tenant_id: str) -> TenantInfo | None:
        """Retrieve a tenant record by ID.

        Args:
            tenant_id: Unique tenant identifier.

        Returns:
            :class:`~lexigram.contracts.tenancy.types.TenantInfo` or ``None``.
        """
        async with self._db.scoped_context() as ctx:
            row = await ctx.fetch_one(
                "SELECT * FROM tenants WHERE tenant_id = :id",
                {"id": tenant_id},
            )
        return self._row_to_tenant(row) if row else None

    async def get_tenant_by_slug(self, slug: str) -> TenantInfo | None:
        """Retrieve a tenant record by slug.

        Args:
            slug: URL-safe tenant identifier.

        Returns:
            :class:`~lexigram.contracts.tenancy.types.TenantInfo` or ``None``.
        """
        async with self._db.scoped_context() as ctx:
            row = await ctx.fetch_one(
                "SELECT * FROM tenants WHERE slug = :slug",
                {"slug": slug},
            )
        return self._row_to_tenant(row) if row else None

    async def list_tenants(self, *, active_only: bool = True) -> list[TenantInfo]:
        """List tenants.

        Args:
            active_only: Return only active tenants when ``True``.

        Returns:
            List of :class:`~lexigram.contracts.tenancy.types.TenantInfo`.
        """
        if active_only:
            query = "SELECT * FROM tenants WHERE status = :status"
            params: dict[str, Any] = {"status": TenantStatus.ACTIVE.value}
        else:
            query = "SELECT * FROM tenants"
            params = {}
        async with self._db.scoped_context() as ctx:
            rows = await ctx.fetch_all(query, params)
        return [self._row_to_tenant(r) for r in rows if r]

    async def create_tenant(
        self, command: CreateTenantCommand
    ) -> Result[TenantInfo, TenantError]:
        """Insert a new tenant record.

        Args:
            command: Creation parameters.

        Returns:
            ``Ok(TenantInfo)`` on success.
        """
        tenant_id = str(uuid4())
        now = datetime.now(UTC)
        async with self._db.scoped_context() as ctx:
            await ctx.execute(
                """INSERT INTO tenants
                   (tenant_id, slug, name, status, plan, config, metadata, created_at)
                   VALUES (:id, :slug, :name, :status, :plan, :config, :metadata, :created_at)""",
                {
                    "id": tenant_id,
                    "slug": command.slug,
                    "name": command.name,
                    "status": TenantStatus.ACTIVE.value,
                    "plan": command.plan,
                    "config": json.dumps(command.config),
                    "metadata": json.dumps(command.metadata),
                    "created_at": now,
                },
            )
        return Ok(
            TenantInfo(
                tenant_id=tenant_id,
                slug=command.slug,
                name=command.name,
                status=TenantStatus.ACTIVE,
                plan=command.plan,
                config=command.config,
                metadata=command.metadata,
                created_at=now,
            )
        )

    async def update_tenant(
        self, tenant_id: str, command: UpdateTenantCommand
    ) -> Result[TenantInfo, TenantError]:
        """Update mutable tenant fields.

        Args:
            tenant_id: Identifier of the tenant to update.
            command: Fields to apply.

        Returns:
            ``Ok(TenantInfo)`` on success, ``Err(TenantNotFoundError)`` if not found.
        """
        existing = await self.get_tenant(tenant_id)
        if existing is None:
            return Err(TenantNotFoundError(tenant_id))
        name = command.name if command.name is not None else existing.name
        plan = command.plan if command.plan is not None else existing.plan
        config = command.config if command.config is not None else existing.config
        metadata = (
            command.metadata if command.metadata is not None else existing.metadata
        )
        async with self._db.scoped_context() as ctx:
            await ctx.execute(
                "UPDATE tenants SET name = :name, plan = :plan, config = :config, "
                "metadata = :metadata WHERE tenant_id = :id",
                {
                    "name": name,
                    "plan": plan,
                    "config": json.dumps(config),
                    "metadata": json.dumps(metadata),
                    "id": tenant_id,
                },
            )
        updated = TenantInfo(
            tenant_id=existing.tenant_id,
            slug=existing.slug,
            name=name,
            status=existing.status,
            plan=plan,
            config=config,
            metadata=metadata,
            created_at=existing.created_at,
        )
        return Ok(updated)

    async def deactivate_tenant(self, tenant_id: str) -> Result[None, TenantError]:
        """Mark tenant inactive.

        Args:
            tenant_id: Tenant to deactivate.

        Returns:
            ``Ok(None)`` on success.
        """
        return await self._set_status(tenant_id, TenantStatus.INACTIVE)

    async def activate_tenant(self, tenant_id: str) -> Result[None, TenantError]:
        """Mark tenant active.

        Args:
            tenant_id: Tenant to activate.

        Returns:
            ``Ok(None)`` on success.
        """
        return await self._set_status(tenant_id, TenantStatus.ACTIVE)

    async def suspend_tenant(
        self, tenant_id: str, reason: str | None = None
    ) -> Result[None, TenantError]:
        """Mark tenant suspended.

        Args:
            tenant_id: Tenant to suspend.
            reason: Optional reason (ignored in SQL impl; use metadata separately).

        Returns:
            ``Ok(None)`` on success.
        """
        return await self._set_status(tenant_id, TenantStatus.SUSPENDED)

    async def _set_status(
        self, tenant_id: str, status: TenantStatus
    ) -> Result[None, TenantError]:
        existing = await self.get_tenant(tenant_id)
        if existing is None:
            return Err(TenantNotFoundError(tenant_id))
        async with self._db.scoped_context() as ctx:
            await ctx.execute(
                "UPDATE tenants SET status = :status WHERE tenant_id = :id",
                {"status": status.value, "id": tenant_id},
            )
        return Ok(None)

    # ------------------------------------------------------------------
    # TenantConfigProviderProtocol
    # ------------------------------------------------------------------

    async def get_config(self, tenant_id: str, key: str) -> Any | None:
        """Get a single config value.

        Args:
            tenant_id: Tenant identifier.
            key: Configuration key.

        Returns:
            Parsed value or ``None``.
        """
        async with self._db.scoped_context() as ctx:
            row = await ctx.fetch_one(
                "SELECT value FROM tenant_configs WHERE tenant_id = :id AND key = :key",
                {"id": tenant_id, "key": key},
            )
        if row:
            raw = row.get("value") if hasattr(row, "get") else row[0]
            return json.loads(raw) if raw is not None else None
        return None

    async def get_all_config(self, tenant_id: str) -> dict[str, Any]:
        """Get all config for a tenant.

        Args:
            tenant_id: Tenant identifier.

        Returns:
            Dict of config key-value pairs.
        """
        async with self._db.scoped_context() as ctx:
            rows = await ctx.fetch_all(
                "SELECT key, value FROM tenant_configs WHERE tenant_id = :id",
                {"id": tenant_id},
            )
        result: dict[str, Any] = {}
        for row in rows:
            k = row.get("key") if hasattr(row, "get") else row[0]
            v = row.get("value") if hasattr(row, "get") else row[1]
            result[k] = json.loads(v) if v is not None else None
        return result

    async def set_config(self, tenant_id: str, key: str, value: Any) -> None:
        """Upsert a config value.

        Args:
            tenant_id: Tenant identifier.
            key: Configuration key.
            value: New value.
        """
        async with self._db.scoped_context() as ctx:
            await ctx.execute(
                """INSERT INTO tenant_configs (tenant_id, key, value)
                   VALUES (:id, :key, :value)
                   ON CONFLICT (tenant_id, key) DO UPDATE SET value = EXCLUDED.value""",
                {"id": tenant_id, "key": key, "value": json.dumps(value)},
            )

    @staticmethod
    def _row_to_tenant(row: Any) -> TenantInfo:
        """Convert a DB row to TenantInfo.

        Args:
            row: Database row (dict-like or tuple).

        Returns:
            Parsed :class:`~lexigram.contracts.tenancy.types.TenantInfo`.
        """
        if hasattr(row, "get"):
            data = dict(row)
        else:
            # Fallback positional — unlikely for modern drivers but safe
            data = dict(row._mapping) if hasattr(row, "_mapping") else {}

        return TenantInfo(
            tenant_id=data["tenant_id"],
            slug=data["slug"],
            name=data["name"],
            status=TenantStatus(data["status"]),
            plan=data.get("plan"),
            config=json.loads(data["config"]) if data.get("config") else {},
            metadata=json.loads(data["metadata"]) if data.get("metadata") else {},
            created_at=data.get("created_at"),
        )


__all__ = ["SQLTenantProvider"]
