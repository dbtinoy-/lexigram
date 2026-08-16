from __future__ import annotations

import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.nosql.backends.firestore.backend import FirestoreBackend
from lexigram.nosql.backends.firestore.repository import FirestoreRepository
from lexigram.nosql.config import FirestoreConfig
from lexigram.nosql.exceptions import NoSQLConnectionError


def _make_config(**kwargs: object) -> FirestoreConfig:
    return FirestoreConfig(
        project_id=kwargs.get("project_id", "test-project"),  # type: ignore[arg-type]
        database_id=kwargs.get("database_id", "(default)"),  # type: ignore[arg-type]
        credentials_json=kwargs.get("credentials_json", None),  # type: ignore[arg-type]
    )


def _make_client_mock() -> MagicMock:
    client = MagicMock()

    async_iter = MagicMock()
    async_iter.__aiter__.return_value = async_iter
    async_iter.__anext__ = AsyncMock(side_effect=StopAsyncIteration)

    client.collections = MagicMock(return_value=async_iter)
    client.close = MagicMock()
    return client


def _ensure_google_packages() -> None:
    """Ensure google and google.cloud module entries exist in sys.modules."""
    if "google" not in sys.modules:
        sys.modules["google"] = types.ModuleType("google")
    if "google.cloud" not in sys.modules:
        sys.modules["google.cloud"] = types.ModuleType("google.cloud")


def _install_firestore_stub(client_mock: MagicMock | None = None) -> MagicMock:
    """Install a google.cloud.firestore_v1 stub in sys.modules and return it."""
    _ensure_google_packages()
    fs = MagicMock()
    fs.AsyncClient = MagicMock(return_value=client_mock or _make_client_mock())
    sys.modules["google.cloud.firestore_v1"] = fs
    return fs


async def _make_connected_backend(config: FirestoreConfig | None = None) -> FirestoreBackend:
    cfg = config or _make_config()
    backend = FirestoreBackend(cfg)
    client_mock = _make_client_mock()
    _install_firestore_stub(client_mock)
    with patch.object(backend, "_probe_connectivity", new_callable=AsyncMock):
        await backend.connect()
    return backend


class TestFirestoreBackendInit:
    def test_init_sets_database_name(self) -> None:
        cfg = _make_config(database_id="mydb")
        backend = FirestoreBackend(cfg)
        assert backend.database_name == "mydb"
        assert backend.is_connected() is False


class TestFirestoreBackendConnect:
    @pytest.mark.asyncio
    async def test_connect_sets_connected_flag(self) -> None:
        backend = await _make_connected_backend()
        assert backend.is_connected() is True

    @pytest.mark.asyncio
    async def test_connect_raises_when_firestore_unavailable(self) -> None:
        cfg = _make_config()
        backend = FirestoreBackend(cfg)

        saved_fs = sys.modules.pop("google.cloud.firestore_v1", None)
        saved_google = sys.modules.pop("google", None)
        saved_cloud = sys.modules.pop("google.cloud", None)
        try:
            with pytest.raises(NoSQLConnectionError, match="google-cloud-firestore is required"):
                await backend.connect()
        finally:
            if saved_fs is not None:
                sys.modules["google.cloud.firestore_v1"] = saved_fs
            if saved_google is not None:
                sys.modules["google"] = saved_google
            if saved_cloud is not None:
                sys.modules["google.cloud"] = saved_cloud

    @pytest.mark.asyncio
    async def test_connect_raises_on_client_failure(self) -> None:
        cfg = _make_config()
        backend = FirestoreBackend(cfg)

        _ensure_google_packages()
        fs = MagicMock()
        fs.AsyncClient = MagicMock(side_effect=RuntimeError("bad config"))
        sys.modules["google.cloud.firestore_v1"] = fs
        with pytest.raises(NoSQLConnectionError, match="Failed to create Firestore client"):
            await backend.connect()

    @pytest.mark.asyncio
    async def test_connect_creates_client_with_project_and_database(self) -> None:
        cfg = _make_config(project_id="my-proj", database_id="my-db")
        backend = FirestoreBackend(cfg)
        client_mock = _make_client_mock()
        fs = _install_firestore_stub(client_mock)

        with patch.object(backend, "_probe_connectivity", new_callable=AsyncMock):
            await backend.connect()

        fs.AsyncClient.assert_called_once_with(project="my-proj", database="my-db")

    @pytest.mark.asyncio
    async def test_connect_uses_credentials_json(self) -> None:
        cfg = _make_config(credentials_json='{"type": "service_account"}')
        backend = FirestoreBackend(cfg)
        client_mock = _make_client_mock()
        _install_firestore_stub(client_mock)

        sys.modules.setdefault("google.oauth2", types.ModuleType("google.oauth2"))
        sys.modules.setdefault("google.oauth2.service_account", MagicMock())

        with patch.object(backend, "_probe_connectivity", new_callable=AsyncMock):
            with patch("google.oauth2.service_account.Credentials.from_service_account_info") as mock_creds:
                await backend.connect()

            mock_creds.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_clears_state(self) -> None:
        backend = await _make_connected_backend()
        await backend.disconnect()
        assert backend._client is None
        assert backend.is_connected() is False

    @pytest.mark.asyncio
    async def test_disconnect_noop_when_not_connected(self) -> None:
        cfg = _make_config()
        backend = FirestoreBackend(cfg)
        await backend.disconnect()


class TestFirestoreBackendCollection:
    @pytest.mark.asyncio
    async def test_collection_returns_firestore_repository(self) -> None:
        backend = await _make_connected_backend()
        col = backend.collection("users")
        assert isinstance(col, FirestoreRepository)

    @pytest.mark.asyncio
    async def test_collection_caches_by_name(self) -> None:
        backend = await _make_connected_backend()
        col_a = backend.collection("items")
        col_b = backend.collection("items")
        assert col_a is col_b

    @pytest.mark.asyncio
    async def test_repository_delegates_to_collection(self) -> None:
        backend = await _make_connected_backend()
        repo = backend.repository("users")
        assert isinstance(repo, FirestoreRepository)

    @pytest.mark.asyncio
    async def test_collection_raises_when_not_connected(self) -> None:
        cfg = _make_config()
        backend = FirestoreBackend(cfg)
        with pytest.raises(RuntimeError, match="not connected"):
            backend.collection("users")


class TestFirestoreBackendLifecycle:
    @pytest.mark.asyncio
    async def test_session_is_noop(self) -> None:
        backend = await _make_connected_backend()
        async with backend.session():
            pass

    @pytest.mark.asyncio
    async def test_list_collections(self) -> None:
        backend = await _make_connected_backend()
        col_refs = [MagicMock(), MagicMock()]
        col_refs[0].id = "users"
        col_refs[1].id = "orders"
        backend._client.collections.return_value.__aiter__.return_value = col_refs

        names = await backend.list_collections()
        assert names == ["users", "orders"]

    @pytest.mark.asyncio
    async def test_list_collections_raises_when_not_connected(self) -> None:
        cfg = _make_config()
        backend = FirestoreBackend(cfg)
        with pytest.raises(RuntimeError, match="not connected"):
            await backend.list_collections()

    @pytest.mark.asyncio
    async def test_drop_collection(self) -> None:
        backend = await _make_connected_backend()
        col_ref = MagicMock()
        backend._client.collection = MagicMock(return_value=col_ref)
        snapshot = MagicMock()
        snapshot.reference.delete = AsyncMock()
        col_ref.limit.return_value.stream.return_value.__aiter__.return_value = [snapshot]

        await backend.drop_collection("temp_data")
        col_ref.limit.assert_called_once_with(500)
        snapshot.reference.delete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_drop_collection_raises_when_not_connected(self) -> None:
        cfg = _make_config()
        backend = FirestoreBackend(cfg)
        with pytest.raises(RuntimeError, match="not connected"):
            await backend.drop_collection("test")


class TestFirestoreBackendHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_healthy(self) -> None:
        backend = await _make_connected_backend()
        with patch.object(backend, "_probe_connectivity", new_callable=AsyncMock):
            result = await backend.health_check()

        assert isinstance(result, HealthCheckResult)
        assert result.component == "firestore"
        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_when_not_connected(self) -> None:
        cfg = _make_config()
        backend = FirestoreBackend(cfg)
        result = await backend.health_check()
        assert result.status == HealthStatus.UNHEALTHY
        assert result.message == "Not connected"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_on_timeout(self) -> None:
        backend = await _make_connected_backend()

        async def _timeout() -> None:
            raise TimeoutError()

        with patch.object(backend, "_probe_connectivity", side_effect=_timeout):
            result = await backend.health_check()

        assert result.status == HealthStatus.UNHEALTHY
        assert "timed out" in (result.message or "")

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_on_failure(self) -> None:
        backend = await _make_connected_backend()

        async def _fail() -> None:
            raise RuntimeError("firestore down")

        with patch.object(backend, "_probe_connectivity", side_effect=_fail):
            result = await backend.health_check()

        assert result.status == HealthStatus.UNHEALTHY
        assert "Health check failed" in (result.message or "")
