from __future__ import annotations

from datetime import UTC, datetime

from lexigram.secrets.types import SecretVersion, VersionedSecret


class AWSSecretsManagerStore:
    """``RotatableSecretStoreProtocol`` backend backed by AWS Secrets Manager.

    Requires the ``aioboto3`` library and valid AWS credentials.
    Maintains a local ``{secret_key: {local_version: aws_version_id}}``
    mapping to project AWS's UUID version identifiers onto sequential integers.

    Example::

        store = AWSSecretsManagerStore(
            region_name="us-east-1",
            aws_access_key_id="AKIA...",
            aws_secret_access_key="...",
        )
        await store.set("db_password", "s3cret")
    """

    def __init__(
        self,
        region_name: str = "us-east-1",
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
    ) -> None:
        self._region_name = region_name
        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key
        self._aws_session_token = aws_session_token
        self._session: object = None
        self._version_map: dict[str, dict[int, str]] = {}
        self._next_version: dict[str, int] = {}

    async def _get_client(self):
        if self._session is None:
            import aioboto3  # type: ignore[import-not-found]

            self._session = aioboto3.Session(
                aws_access_key_id=self._aws_access_key_id,
                aws_secret_access_key=self._aws_secret_access_key,
                aws_session_token=self._aws_session_token,
                region_name=self._region_name,
            )
        return await self._session.client("secretsmanager")

    async def get(self, name: str) -> str | None:
        import botocore.exceptions

        client = await self._get_client()
        try:
            response = await client.get_secret_value(SecretId=name)
        except botocore.exceptions.ClientError:
            return None
        return response.get("SecretString")

    async def get_bulk(self, *names: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for name in names:
            val = await self.get(name)
            if val is not None:
                result[name] = val
        return result

    async def set(self, name: str, value: str) -> None:
        import botocore.exceptions

        client = await self._get_client()
        try:
            await client.create_secret(
                Name=name,
                SecretString=value,
            )
        except botocore.exceptions.ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code == "ResourceExistsException":
                await client.update_secret(
                    SecretId=name,
                    SecretString=value,
                )
            else:
                raise

    async def delete(self, name: str) -> None:
        import botocore.exceptions

        client = await self._get_client()
        try:
            await client.delete_secret(SecretId=name, ForceDeleteWithoutRecovery=True)
        except botocore.exceptions.ClientError:
            pass
        self._version_map.pop(name, None)
        self._next_version.pop(name, None)

    async def rotate(self, key: str) -> VersionedSecret:
        import secrets as stdlib_secrets

        from lexigram.security.secrets.store import SecretValue

        new_value = SecretValue(stdlib_secrets.token_hex(32))
        client = await self._get_client()
        response = await client.put_secret_value(
            SecretId=key,
            SecretString=str(new_value),
        )
        aws_version_id = response.get("VersionId", "")
        ver_num = self._next_version.get(key, 1)
        self._next_version[key] = ver_num + 1
        self._version_map.setdefault(key, {})[ver_num] = aws_version_id
        return await self.get_current_version(key)

    async def get_version(self, key: str, version: int) -> str | None:
        aws_version_id = self._version_map.get(key, {}).get(version)
        if aws_version_id is None:
            return None
        import botocore.exceptions

        client = await self._get_client()
        try:
            response = await client.get_secret_value(
                SecretId=key,
                VersionId=aws_version_id,
            )
        except botocore.exceptions.ClientError:
            return None
        return response.get("SecretString")

    async def list_versions(self, key: str) -> list[SecretVersion]:
        import botocore.exceptions

        client = await self._get_client()
        try:
            response = await client.list_secret_version_ids(SecretId=key)
        except botocore.exceptions.ClientError:
            return []
        # Build a lookup: aws_version_id -> created_date
        aws_entries: dict[str, datetime] = {}
        for entry in response.get("Versions", []):
            vid = entry.get("VersionId", "")
            created = entry.get("CreatedDate")
            if created:
                aws_entries[vid] = created.replace(tzinfo=UTC)
        # Map through local version map
        local_map = self._version_map.get(key, {})
        versions: list[SecretVersion] = []
        for local_ver, aws_vid in local_map.items():
            created_at = aws_entries.get(aws_vid, datetime.now(UTC))
            versions.append(SecretVersion(version=local_ver, created_at=created_at))
        versions.sort(key=lambda sv: sv.version, reverse=True)
        return versions

    async def get_current_version(self, key: str) -> VersionedSecret:
        import botocore.exceptions

        from lexigram.security.secrets.store import SecretValue

        client = await self._get_client()
        try:
            response = await client.get_secret_value(SecretId=key)
        except botocore.exceptions.ClientError as exc:
            msg = f"Secret '{key}' not found"
            raise KeyError(msg) from exc
        secret_string = response.get("SecretString", "")
        aws_version_id = response.get("VersionId", "")
        created = response.get("CreatedDate")
        created_at = created.replace(tzinfo=UTC) if created else datetime.now(UTC)
        # Find the local version number for this AWS version ID
        local_map = self._version_map.get(key, {})
        local_ver = 0
        for lv, avid in local_map.items():
            if avid == aws_version_id:
                local_ver = lv
                break
        return VersionedSecret(
            key=key,
            version=local_ver,
            value=SecretValue(str(secret_string)),
            created_at=created_at,
        )
