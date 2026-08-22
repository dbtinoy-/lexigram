from __future__ import annotations

import asyncio
from datetime import UTC
from typing import Any

from lexigram.secrets.exceptions import SecretBackendUnavailableError
from lexigram.secrets.types import SecretVersion, VersionedSecret


def _is_not_found(exc: Exception) -> bool:
    try:
        from hvac.exceptions import InvalidPath
    except ImportError:  # pragma: no cover - hvac is a lazy dependency
        return False
    return isinstance(exc, InvalidPath)


class HashicorpVaultStore:
    """``RotatableSecretStoreProtocol`` backend backed by Hashicorp Vault KV v2.

    Requires the ``hvac`` library and a running Vault instance.

    Example::

        store = HashicorpVaultStore(
            url="http://127.0.0.1:8200",
            token="root-token",
            mount_point="secret",
        )
        await store.set("db_password", "s3cret")
    """

    def __init__(
        self,
        url: str,
        token: str,
        mount_point: str = "secret",
    ) -> None:
        self._url = url
        self._token = token
        self._mount_point = mount_point
        self._client: object = None  # hvac.Client, lazy-initialized

    def _get_client(self) -> Any:  # noqa: ANN202
        if self._client is None:
            import hvac

            self._client = hvac.Client(url=self._url, token=self._token)
        return self._client

    def _path(self, name: str) -> str:
        return f"{self._mount_point}/data/{name}"

    async def get(self, name: str) -> str | None:
        client = self._get_client()
        try:
            response = await asyncio.to_thread(
                client.secrets.kv.v2.read_secret_version,
                path=name,
                mount_point=self._mount_point,
            )
        except Exception as exc:  # noqa: BLE001 — must distinguish not-found from backend failure
            if _is_not_found(exc):
                return None
            raise SecretBackendUnavailableError(
                f"Vault read failed for {name!r}: {exc}"
            ) from exc
        data = response.get("data", {}).get("data", {})
        if not data:
            return None
        return str(data.get("value", ""))

    async def get_bulk(self, *names: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for name in names:
            val = await self.get(name)
            if val is not None:
                result[name] = val
        return result

    async def set(self, name: str, value: str) -> None:
        client = self._get_client()
        await asyncio.to_thread(
            client.secrets.kv.v2.create_or_update_secret,
            path=name,
            secret={"value": value},
            mount_point=self._mount_point,
        )

    async def delete(self, name: str) -> None:
        client = self._get_client()
        try:
            await asyncio.to_thread(
                client.secrets.kv.v2.delete_metadata_and_all_versions,
                path=name,
                mount_point=self._mount_point,
            )
        except Exception as exc:  # noqa: BLE001 — idempotent delete for missing secrets only
            if _is_not_found(exc):
                return
            raise SecretBackendUnavailableError(
                f"Vault delete failed for {name!r}: {exc}"
            ) from exc

    async def rotate(self, key: str) -> VersionedSecret:
        import secrets as stdlib_secrets

        from lexigram.security.secrets.store import SecretValue

        new_value = SecretValue(stdlib_secrets.token_hex(32))
        await self.set(key, str(new_value))
        return await self.get_current_version(key)

    async def get_version(self, key: str, version: int) -> str | None:
        client = self._get_client()
        try:
            response = await asyncio.to_thread(
                client.secrets.kv.v2.read_secret_version,
                path=key,
                version=version,
                mount_point=self._mount_point,
            )
        except Exception as exc:  # noqa: BLE001 — must distinguish not-found from backend failure
            if _is_not_found(exc):
                return None
            raise SecretBackendUnavailableError(
                f"Vault read failed for {key!r} v{version}: {exc}"
            ) from exc
        data = response.get("data", {}).get("data", {})
        if not data:
            return None
        return str(data.get("value", ""))

    async def list_versions(self, key: str) -> list[SecretVersion]:
        client = self._get_client()
        try:
            metadata = await asyncio.to_thread(
                client.secrets.kv.v2.read_secret_metadata,
                path=key,
                mount_point=self._mount_point,
            )
        except Exception as exc:  # noqa: BLE001 — must distinguish not-found from backend failure
            if _is_not_found(exc):
                return []
            raise SecretBackendUnavailableError(
                f"Vault metadata read failed for {key!r}: {exc}"
            ) from exc
        raw_versions = metadata.get("data", {}).get("versions", {})
        result: list[SecretVersion] = []
        for ver_str, ver_data in raw_versions.items():
            destroyed = ver_data.get("destroyed", False)
            if destroyed:
                continue
            created_time_str = ver_data.get("created_time", "")
            if created_time_str:
                from datetime import datetime

                created_at = datetime.fromisoformat(
                    created_time_str.replace("Z", "+00:00")
                )
            else:
                from datetime import datetime

                created_at = datetime.now(UTC)
            result.append(SecretVersion(version=int(ver_str), created_at=created_at))
        result.sort(key=lambda sv: sv.version, reverse=True)
        return result

    async def get_current_version(self, key: str) -> VersionedSecret:
        from datetime import datetime

        from lexigram.security.secrets.store import SecretValue

        client = self._get_client()
        try:
            response = await asyncio.to_thread(
                client.secrets.kv.v2.read_secret_version,
                path=key,
                mount_point=self._mount_point,
            )
        except Exception as exc:  # noqa: BLE001 — must distinguish not-found from backend failure
            if _is_not_found(exc):
                msg = f"Secret '{key}' not found"
                raise KeyError(msg) from exc
            raise SecretBackendUnavailableError(
                f"Vault read failed for {key!r}: {exc}"
            ) from exc
        data = response.get("data", {})
        secret_data = data.get("data", {})
        if not secret_data:
            msg = f"Secret '{key}' not found"
            raise KeyError(msg)
        value = str(secret_data.get("value", ""))
        meta = data.get("metadata", {})
        version = int(meta.get("version", 0))
        created_time_str = meta.get("created_time", "")
        if created_time_str:
            created_at = datetime.fromisoformat(created_time_str.replace("Z", "+00:00"))
        else:
            created_at = datetime.now(UTC)
        return VersionedSecret(
            key=key,
            version=version,
            value=SecretValue(value),
            created_at=created_at,
        )
