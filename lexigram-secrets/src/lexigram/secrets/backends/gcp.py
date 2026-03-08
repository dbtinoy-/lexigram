from __future__ import annotations

from datetime import UTC, datetime

from lexigram.secrets.types import SecretVersion, VersionedSecret


class GCPSecretManagerStore:
    """``RotatableSecretStoreProtocol`` backend backed by GCP Secret Manager.

    Requires the ``google-cloud-secret-manager`` library and valid GCP
    credentials (via ADC or explicit service account).

    Example::

        store = GCPSecretManagerStore(
            project_id="my-project",
        )
        await store.set("db_password", "s3cret")
    """

    def __init__(self, project_id: str) -> None:
        self._project_id = project_id
        self._client: object = None

    async def _get_client(self):
        if self._client is None:
            from google.cloud import secretmanager

            self._client = secretmanager.SecretManagerServiceAsyncClient()
        return self._client

    def _secret_path(self, name: str) -> str:
        return f"projects/{self._project_id}/secrets/{name}"

    def _version_path(self, name: str, version: str = "latest") -> str:
        return f"{self._secret_path(name)}/versions/{version}"

    async def get(self, name: str) -> str | None:
        from grpc import RpcError  # type: ignore[import-untyped]

        client = await self._get_client()
        try:
            response = await client.access_secret_version(
                request={"name": self._version_path(name)}
            )
        except RpcError:
            return None
        payload = response.payload
        if payload is None:
            return None
        return payload.data.decode("utf-8")

    async def get_bulk(self, *names: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for name in names:
            val = await self.get(name)
            if val is not None:
                result[name] = val
        return result

    async def set(self, name: str, value: str) -> None:

        from grpc import RpcError

        client = await self._get_client()
        parent = f"projects/{self._project_id}"
        try:
            await client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": name,
                    "secret": {"replication": {"automatic": {}}},
                }
            )
        except RpcError:
            pass
        await client.add_secret_version(
            request={
                "parent": self._secret_path(name),
                "payload": {"data": value.encode("utf-8")},
            }
        )

    async def delete(self, name: str) -> None:
        from grpc import RpcError

        client = await self._get_client()
        try:
            await client.delete_secret(request={"name": self._secret_path(name)})
        except RpcError:
            pass

    async def rotate(self, key: str) -> VersionedSecret:
        import secrets as stdlib_secrets

        from lexigram.security.secrets.store import SecretValue

        new_value = SecretValue(stdlib_secrets.token_hex(32))
        await self.set(key, str(new_value))
        return await self.get_current_version(key)

    async def get_version(self, key: str, version: int) -> str | None:
        from grpc import RpcError

        client = await self._get_client()
        try:
            response = await client.access_secret_version(
                request={"name": self._version_path(key, str(version))}
            )
        except RpcError:
            return None
        payload = response.payload
        if payload is None:
            return None
        return payload.data.decode("utf-8")

    async def list_versions(self, key: str) -> list[SecretVersion]:
        from grpc import RpcError

        client = await self._get_client()
        try:
            response = await client.list_secret_versions(
                request={"parent": self._secret_path(key)}
            )
        except RpcError:
            return []
        versions: list[SecretVersion] = []
        async for version in response:
            created_at = (
                version.create_time.replace(tzinfo=UTC)
                if version.create_time
                else datetime.now(UTC)
            )
            parts = version.name.split("/")
            ver_str = parts[-1] if parts else "0"
            versions.append(SecretVersion(version=int(ver_str), created_at=created_at))
        versions.sort(key=lambda sv: sv.version, reverse=True)
        return versions

    async def get_current_version(self, key: str) -> VersionedSecret:
        from grpc import RpcError

        from lexigram.security.secrets.store import SecretValue

        client = await self._get_client()
        try:
            response = await client.access_secret_version(
                request={"name": self._version_path(key)}
            )
        except RpcError as exc:
            msg = f"Secret '{key}' not found"
            raise KeyError(msg) from exc
        payload = response.payload
        if payload is None:
            msg = f"Secret '{key}' not found"
            raise KeyError(msg)
        value = payload.data.decode("utf-8")
        parts = response.name.split("/")
        ver_str = parts[-1] if parts else "0"
        created_at = (
            response.create_time.replace(tzinfo=UTC)
            if hasattr(response, "create_time") and response.create_time
            else datetime.now(UTC)
        )
        return VersionedSecret(
            key=key,
            version=int(ver_str),
            value=SecretValue(value),
            created_at=created_at,
        )
