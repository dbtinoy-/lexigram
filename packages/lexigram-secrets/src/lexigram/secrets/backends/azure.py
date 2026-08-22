from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from lexigram.secrets.types import SecretVersion, VersionedSecret


class AzureKeyVaultStore:
    """``RotatableSecretStoreProtocol`` backend backed by Azure Key Vault.

    Requires the ``azure-keyvault-secrets`` and ``azure-identity`` libraries
    and a valid Azure Key Vault URL.
    Maintains a local ``{secret_key: {local_version: azure_version_id}}``
    mapping to project Azure's UUID version identifiers onto sequential integers.

    Example::

        store = AzureKeyVaultStore(
            vault_url="https://my-vault.vault.azure.net",
        )
        await store.set("db_password", "s3cret")
    """

    def __init__(
        self,
        vault_url: str,
        tenant_id: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        self._vault_url = vault_url
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._client: object = None
        self._version_map: dict[str, dict[int, str]] = {}
        self._next_version: dict[str, int] = {}

    async def _get_client(self) -> Any:
        if self._client is None:
            from azure.identity import (
                ClientSecretCredential,
                DefaultAzureCredential,
            )
            from azure.keyvault.secrets import (
                SecretClient,
            )

            if self._tenant_id and self._client_id and self._client_secret:
                credential = ClientSecretCredential(
                    tenant_id=self._tenant_id,
                    client_id=self._client_id,
                    client_secret=self._client_secret,
                )
            else:
                credential = DefaultAzureCredential()
            self._client = SecretClient(
                vault_url=self._vault_url, credential=credential
            )
        return self._client

    async def get(self, name: str) -> str | None:
        from azure.core.exceptions import (
            ResourceNotFoundError,
        )

        client = await self._get_client()
        try:
            secret = await client.get_secret(name)
        except ResourceNotFoundError:
            return None
        value: str | None = secret.value
        return value

    async def get_bulk(self, *names: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for name in names:
            val = await self.get(name)
            if val is not None:
                result[name] = val
        return result

    async def set(self, name: str, value: str) -> None:
        client = await self._get_client()
        secret = await client.set_secret(name, value)
        azure_version_id = secret.properties.version or ""
        ver_num = self._next_version.get(name, 1)
        self._next_version[name] = ver_num + 1
        self._version_map.setdefault(name, {})[ver_num] = azure_version_id

    async def delete(self, name: str) -> None:
        from azure.core.exceptions import (
            ResourceNotFoundError,
        )

        client = await self._get_client()
        try:
            await client.delete_secret(name)
        except ResourceNotFoundError:
            pass
        self._version_map.pop(name, None)
        self._next_version.pop(name, None)

    async def rotate(self, key: str) -> VersionedSecret:
        import secrets as stdlib_secrets

        from lexigram.security.secrets.store import SecretValue

        new_value = SecretValue(stdlib_secrets.token_hex(32))
        await self.set(key, str(new_value))
        return await self.get_current_version(key)

    async def get_version(self, key: str, version: int) -> str | None:
        azure_version_id = self._version_map.get(key, {}).get(version)
        if azure_version_id is None:
            return None
        from azure.core.exceptions import (
            ResourceNotFoundError,
        )

        client = await self._get_client()
        try:
            secret = await client.get_secret(key, version=azure_version_id)
        except ResourceNotFoundError:
            return None
        value: str | None = secret.value
        return value

    async def list_versions(self, key: str) -> list[SecretVersion]:
        from azure.core.exceptions import (
            ResourceNotFoundError,
        )

        client = await self._get_client()
        try:
            versions = client.list_properties_of_secret_versions(key)
        except ResourceNotFoundError:
            return []
        # Build lookup: azure_version_id -> created_on
        azure_entries: dict[str, datetime] = {}
        async for version_props in versions:
            vid = version_props.version or ""
            created = version_props.created_on
            if created:
                azure_entries[vid] = created.replace(tzinfo=UTC)
        local_map = self._version_map.get(key, {})
        result: list[SecretVersion] = []
        for local_ver, avid in local_map.items():
            created_at = azure_entries.get(avid, datetime.now(UTC))
            result.append(SecretVersion(version=local_ver, created_at=created_at))
        result.sort(key=lambda sv: sv.version, reverse=True)
        return result

    async def get_current_version(self, key: str) -> VersionedSecret:
        from azure.core.exceptions import (
            ResourceNotFoundError,
        )

        from lexigram.security.secrets.store import SecretValue

        client = await self._get_client()
        try:
            secret = await client.get_secret(key)
        except ResourceNotFoundError as exc:
            msg = f"Secret '{key}' not found"
            raise KeyError(msg) from exc
        azure_version_id = secret.properties.version or ""
        created_at = (
            secret.properties.created_on.replace(tzinfo=UTC)
            if secret.properties.created_on
            else datetime.now(UTC)
        )
        local_map = self._version_map.get(key, {})
        local_ver = 0
        for lv, avid in local_map.items():
            if avid == azure_version_id:
                local_ver = lv
                break
        return VersionedSecret(
            key=key,
            version=local_ver,
            value=SecretValue(str(secret.value)),
            created_at=created_at,
        )
