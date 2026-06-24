"""Cloud secret backends must distinguish NotFound from real failures (audit §10 F5)."""

from __future__ import annotations

import enum
import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.secrets.backends.gcp import GCPSecretManagerStore
from lexigram.secrets.backends.vault import HashicorpVaultStore
from lexigram.secrets.exceptions import SecretBackendUnavailableError

# Lazy-imported SDKs are not installed in the test environment; stub the
# modules so backends can classify exceptions without the real SDKs.
_GRPC_RPC_ERROR = types.ModuleType("grpc")
_GRPC_RPC_ERROR.RpcError = type("RpcError", (Exception,), {})
_GRPC_RPC_ERROR.StatusCode = enum.Enum(
    "StatusCode",
    "OK UNKNOWN NOT_FOUND ALREADY_EXISTS PERMISSION_DENIED UNAUTHENTICATED",
)

_HVAC = types.ModuleType("hvac")
_HVAC_EXCEPTIONS = types.ModuleType("hvac.exceptions")
_HVAC_EXCEPTIONS.InvalidPath = type("InvalidPath", (Exception,), {})
_HVAC.exceptions = _HVAC_EXCEPTIONS


@pytest.fixture(autouse=True)
def _stub_lazy_sdks(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "grpc", _GRPC_RPC_ERROR)
    monkeypatch.setitem(sys.modules, "hvac", _HVAC)
    monkeypatch.setitem(sys.modules, "hvac.exceptions", _HVAC_EXCEPTIONS)


def _rpc_error(status: enum.Enum) -> Exception:
    exc = _GRPC_RPC_ERROR.RpcError("backend failure")
    exc.code = lambda: status
    return exc


class TestGcpBackendFailClosed:
    @pytest.fixture
    def store(self) -> GCPSecretManagerStore:
        store = GCPSecretManagerStore(project_id="test-project")
        store._client = AsyncMock()
        return store

    @pytest.mark.asyncio
    async def test_auth_failure_is_not_swallowed_as_not_found(self, store) -> None:
        store._client.access_secret_version.side_effect = _rpc_error(
            _GRPC_RPC_ERROR.StatusCode.PERMISSION_DENIED
        )
        with pytest.raises(SecretBackendUnavailableError):
            await store.get("db_password")

    @pytest.mark.asyncio
    async def test_missing_secret_returns_none(self, store) -> None:
        store._client.access_secret_version.side_effect = _rpc_error(
            _GRPC_RPC_ERROR.StatusCode.NOT_FOUND
        )
        assert await store.get("db_password") is None

    @pytest.mark.asyncio
    async def test_list_versions_auth_failure_raises(self, store) -> None:
        store._client.list_secret_versions.side_effect = _rpc_error(
            _GRPC_RPC_ERROR.StatusCode.UNAUTHENTICATED
        )
        with pytest.raises(SecretBackendUnavailableError):
            await store.list_versions("db_password")

    @pytest.mark.asyncio
    async def test_list_versions_missing_returns_empty(self, store) -> None:
        store._client.list_secret_versions.side_effect = _rpc_error(
            _GRPC_RPC_ERROR.StatusCode.NOT_FOUND
        )
        assert await store.list_versions("db_password") == []

    @pytest.mark.asyncio
    async def test_get_current_version_auth_failure_raises(self, store) -> None:
        store._client.access_secret_version.side_effect = _rpc_error(
            _GRPC_RPC_ERROR.StatusCode.PERMISSION_DENIED
        )
        with pytest.raises(SecretBackendUnavailableError):
            await store.get_current_version("db_password")

    @pytest.mark.asyncio
    async def test_get_current_version_missing_keeps_keyerror(self, store) -> None:
        store._client.access_secret_version.side_effect = _rpc_error(
            _GRPC_RPC_ERROR.StatusCode.NOT_FOUND
        )
        with pytest.raises(KeyError):
            await store.get_current_version("db_password")

    @pytest.mark.asyncio
    async def test_set_already_exists_is_idempotent(self, store) -> None:
        store._client.create_secret.side_effect = _rpc_error(
            _GRPC_RPC_ERROR.StatusCode.ALREADY_EXISTS
        )
        store._client.add_secret_version = AsyncMock()
        await store.set("db_password", "s3cret")
        store._client.add_secret_version.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_set_auth_failure_raises(self, store) -> None:
        store._client.create_secret.side_effect = _rpc_error(
            _GRPC_RPC_ERROR.StatusCode.PERMISSION_DENIED
        )
        with pytest.raises(SecretBackendUnavailableError):
            await store.set("db_password", "s3cret")


class TestVaultBackendErrorDistinction:
    @pytest.fixture
    def store(self) -> HashicorpVaultStore:
        store = HashicorpVaultStore(url="http://localhost:8200", token="test")
        store._client = MagicMock()
        return store

    @pytest.mark.asyncio
    async def test_auth_failure_raises_typed_error(self, store) -> None:
        store._client.secrets.kv.v2.read_secret_version.side_effect = RuntimeError(
            "connection refused"
        )
        with pytest.raises(SecretBackendUnavailableError):
            await store.get("db_password")

    @pytest.mark.asyncio
    async def test_not_found_returns_none(self, store) -> None:
        store._client.secrets.kv.v2.read_secret_version.side_effect = (
            _HVAC_EXCEPTIONS.InvalidPath("secret not found")
        )
        assert await store.get("db_password") is None

    @pytest.mark.asyncio
    async def test_list_versions_auth_failure_raises(self, store) -> None:
        store._client.secrets.kv.v2.read_secret_metadata.side_effect = PermissionError()
        with pytest.raises(SecretBackendUnavailableError):
            await store.list_versions("db_password")

    @pytest.mark.asyncio
    async def test_list_versions_not_found_returns_empty(self, store) -> None:
        store._client.secrets.kv.v2.read_secret_metadata.side_effect = (
            _HVAC_EXCEPTIONS.InvalidPath("secret not found")
        )
        assert await store.list_versions("db_password") == []

    @pytest.mark.asyncio
    async def test_get_current_version_not_found_keeps_keyerror(self, store) -> None:
        store._client.secrets.kv.v2.read_secret_version.side_effect = (
            _HVAC_EXCEPTIONS.InvalidPath("secret not found")
        )
        with pytest.raises(KeyError):
            await store.get_current_version("db_password")

    @pytest.mark.asyncio
    async def test_delete_not_found_is_silent(self, store) -> None:
        store._client.secrets.kv.v2.delete_metadata_and_all_versions.side_effect = (
            _HVAC_EXCEPTIONS.InvalidPath("secret not found")
        )
        await store.delete("db_password")

    @pytest.mark.asyncio
    async def test_delete_auth_failure_raises(self, store) -> None:
        store._client.secrets.kv.v2.delete_metadata_and_all_versions.side_effect = (
            PermissionError()
        )
        with pytest.raises(SecretBackendUnavailableError):
            await store.delete("db_password")
