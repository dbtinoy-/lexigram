from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.secrets.types import (
        RotatableSecretStoreProtocol,
        SecretVersion,
        VersionedSecret,
    )


class TenantScopedSecretStore:
    """Wraps a ``RotatableSecretStoreProtocol``, prefixing all secret names
    with ``tenant_id/`` to isolate secrets per tenant.

    Example::
        tenant_a_store = TenantScopedSecretStore(store, "tenant_a")
        await tenant_a_store.set("db_password", "s3cret")
        # internally stored as "tenant_a/db_password"
    """

    def __init__(
        self,
        store: RotatableSecretStoreProtocol,
        tenant_id: str,
    ) -> None:
        self._store = store
        self._prefix = f"{tenant_id}/"

    def _qualify(self, key: str) -> str:
        return f"{self._prefix}{key}"

    def _unqualify(self, key: str) -> str:
        if key.startswith(self._prefix):
            return key[len(self._prefix) :]
        return key

    async def get(self, name: str) -> str | None:
        return await self._store.get(self._qualify(name))

    async def get_bulk(self, *names: str) -> dict[str, str]:
        raw = await self._store.get_bulk(*[self._qualify(n) for n in names])
        return {self._unqualify(k): v for k, v in raw.items()}

    async def set(self, name: str, value: str) -> None:
        await self._store.set(self._qualify(name), value)

    async def delete(self, name: str) -> None:
        await self._store.delete(self._qualify(name))

    async def rotate(self, key: str) -> VersionedSecret:
        result = await self._store.rotate(self._qualify(key))
        return self._replace_key(result, key)

    async def get_version(self, key: str, version: int) -> str | None:
        return await self._store.get_version(self._qualify(key), version)

    async def list_versions(self, key: str) -> list[SecretVersion]:
        return await self._store.list_versions(self._qualify(key))

    async def get_current_version(self, key: str) -> VersionedSecret:
        result = await self._store.get_current_version(self._qualify(key))
        return self._replace_key(result, key)

    def _replace_key(self, secret: VersionedSecret, new_key: str) -> VersionedSecret:
        import dataclasses

        return dataclasses.replace(secret, key=new_key)
