from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from lexigram.contracts.audit.types import AuditEntry, AuditEventSeverity
from lexigram.primitives.context import CORRELATION_ID, TENANT_ID, Context

if TYPE_CHECKING:
    from lexigram.secrets.types import (
        RotatableSecretStoreProtocol,
        SecretVersion,
        VersionedSecret,
    )


class AuditLoggerProtocol(Protocol):
    """Minimal audit logger accepted by ``SecretAuditDecorator``."""

    async def log(self, entry: AuditEntry) -> None: ...


class SecretAuditDecorator:
    """Wraps a ``RotatableSecretStoreProtocol``, logging all operations
    via an ``AuditLoggerProtocol``.

    Every read, write, delete, and rotation produces an ``AuditEntry``
    with the action, the secret name, and a timestamp.
    """

    def __init__(
        self,
        store: RotatableSecretStoreProtocol,
        logger: AuditLoggerProtocol,
        actor_id: str = "secrets-system",
        context: Context | None = None,
    ) -> None:
        self._store = store
        self._logger = logger
        self._actor_id = actor_id
        self._context = context

    def _entry(self, action: str, resource_id: str = "") -> AuditEntry:
        tenant_id: str | None = None
        correlation_id: str | None = None
        if self._context is not None:
            tenant_id = self._context.get(TENANT_ID)
            correlation_id = self._context.get(CORRELATION_ID)
        return AuditEntry(
            action=action,
            actor_id=self._actor_id,
            resource_type="secret",
            resource_id=resource_id,
            severity=AuditEventSeverity.MEDIUM,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )

    async def get(self, name: str) -> str | None:
        value = await self._store.get(name)
        await self._logger.log(self._entry("secret.get", name))
        return value

    async def get_bulk(self, *names: str) -> dict[str, str]:
        result = await self._store.get_bulk(*names)
        for n in names:
            await self._logger.log(self._entry("secret.get", n))
        return result

    async def set(self, name: str, value: str) -> None:
        await self._store.set(name, value)
        await self._logger.log(self._entry("secret.set", name))

    async def delete(self, name: str) -> None:
        await self._store.delete(name)
        await self._logger.log(self._entry("secret.delete", name))

    async def rotate(self, key: str) -> VersionedSecret:
        result = await self._store.rotate(key)
        await self._logger.log(self._entry("secret.rotate", key))
        return result

    async def get_version(self, key: str, version: int) -> str | None:
        value = await self._store.get_version(key, version)
        await self._logger.log(self._entry("secret.get_version", f"{key} v{version}"))
        return value

    async def list_versions(self, key: str) -> list[SecretVersion]:
        versions = await self._store.list_versions(key)
        await self._logger.log(self._entry("secret.list_versions", key))
        return versions

    async def get_current_version(self, key: str) -> VersionedSecret:
        result = await self._store.get_current_version(key)
        await self._logger.log(self._entry("secret.get_current_version", key))
        return result
