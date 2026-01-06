"""Tests for PoolHealthController."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request

from lexigram.admin.controllers.pool_health import PoolHealthController
from lexigram.serialization import loads


class _FakeStats:
    """Mimic a pool stats object returned by PoolManager."""

    pool_utilization: float
    total_connections: int
    active_connections: int
    idle_connections: int
    created_connections: int
    destroyed_connections: int
    last_health_check: str | None = None

    def __init__(self, **kwargs: float | str | None) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


def _mock_request(**overrides: str) -> Request:
    """Build a minimal Request stub with path_params."""
    req = MagicMock(spec=Request)
    req.path_params = overrides
    return req


class TestPoolHealthController:
    """Tests for PoolHealthController."""

    @pytest.fixture
    def renderer(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def pool_manager(self) -> MagicMock:
        pm = MagicMock()
        pm.get_stats.return_value = {
            "main": _FakeStats(
                pool_utilization=45.0,
                total_connections=20,
                active_connections=9,
                idle_connections=11,
                created_connections=100,
                destroyed_connections=80,
                last_health_check="2026-01-01T00:00:00",
            ),
            "secondary": _FakeStats(
                pool_utilization=92.0,
                total_connections=10,
                active_connections=10,
                idle_connections=0,
                created_connections=50,
                destroyed_connections=40,
                last_health_check=None,
            ),
        }
        pm.get_pool = AsyncMock()
        return pm

    @pytest.fixture
    def controller(
        self, renderer: MagicMock, pool_manager: MagicMock
    ) -> PoolHealthController:
        return PoolHealthController(
            renderer=renderer,
            pool_manager=pool_manager,
        )

    @pytest.fixture
    def controller_no_pm(self, renderer: MagicMock) -> PoolHealthController:
        return PoolHealthController(renderer=renderer, pool_manager=None)

    # -- get_all_health --

    @pytest.mark.asyncio
    async def test_get_all_health(
        self, controller: PoolHealthController
    ) -> None:
        resp = await controller.get_all_health(_mock_request())
        assert resp.status_code == 200
        data = loads(resp.body)
        assert data["summary"]["total_pools"] == 2
        assert data["summary"]["healthy_pools"] == 1
        assert data["summary"]["unhealthy_pools"] == 1

    @pytest.mark.asyncio
    async def test_get_all_health_503_when_no_manager(
        self, controller_no_pm: PoolHealthController
    ) -> None:
        resp = await controller_no_pm.get_all_health(_mock_request())
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_get_all_health_500_on_error(
        self, renderer: MagicMock, pool_manager: MagicMock
    ) -> None:
        pool_manager.get_stats.side_effect = RuntimeError("boom")
        controller = PoolHealthController(
            renderer=renderer, pool_manager=pool_manager
        )
        resp = await controller.get_all_health(_mock_request())
        assert resp.status_code == 500
        data = loads(resp.body)
        assert "boom" in data["detail"]

    # -- get_pool_health --

    @pytest.mark.asyncio
    async def test_get_pool_health(
        self, controller: PoolHealthController, pool_manager: MagicMock
    ) -> None:
        pool = MagicMock()
        pool.get_stats.return_value = _FakeStats(pool_utilization=30.0)
        pool_manager.get_pool = AsyncMock(return_value=pool)

        resp = await controller.get_pool_health(_mock_request(name="main"))
        assert resp.status_code == 200
        data = loads(resp.body)
        assert data["is_healthy"] is True

    @pytest.mark.asyncio
    async def test_get_pool_health_unhealthy(
        self, controller: PoolHealthController, pool_manager: MagicMock
    ) -> None:
        pool = MagicMock()
        pool.get_stats.return_value = _FakeStats(pool_utilization=95.0)
        pool_manager.get_pool = AsyncMock(return_value=pool)

        resp = await controller.get_pool_health(_mock_request(name="main"))
        assert resp.status_code == 200
        data = loads(resp.body)
        assert data["is_healthy"] is False

    @pytest.mark.asyncio
    async def test_get_pool_health_missing_name(
        self, controller: PoolHealthController
    ) -> None:
        resp = await controller.get_pool_health(_mock_request())
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_get_pool_health_404(
        self, controller: PoolHealthController, pool_manager: MagicMock
    ) -> None:
        pool_manager.get_pool.side_effect = KeyError("main")
        resp = await controller.get_pool_health(_mock_request(name="missing"))
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_pool_health_503_when_no_manager(
        self, controller_no_pm: PoolHealthController
    ) -> None:
        resp = await controller_no_pm.get_pool_health(
            _mock_request(name="main")
        )
        assert resp.status_code == 503

    # -- reconnect_pool --

    @pytest.mark.asyncio
    async def test_reconnect_pool(
        self, controller: PoolHealthController, pool_manager: MagicMock
    ) -> None:
        pool = MagicMock()
        pool.close = AsyncMock()
        pool_manager.get_pool = AsyncMock(return_value=pool)

        resp = await controller.reconnect_pool(_mock_request(name="main"))
        assert resp.status_code == 200
        pool.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reconnect_pool_missing_name(
        self, controller: PoolHealthController
    ) -> None:
        resp = await controller.reconnect_pool(_mock_request())
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_reconnect_pool_404(
        self, controller: PoolHealthController, pool_manager: MagicMock
    ) -> None:
        pool_manager.get_pool.side_effect = KeyError("main")
        resp = await controller.reconnect_pool(_mock_request(name="main"))
        assert resp.status_code == 404

    # -- get_pool_stats_summary --

    @pytest.mark.asyncio
    async def test_get_pool_stats_summary(
        self, controller: PoolHealthController
    ) -> None:
        resp = await controller.get_pool_stats_summary(_mock_request())
        assert resp.status_code == 200
        data = loads(resp.body)
        assert data["total_connections"] == 30  # 20 + 10
        assert data["active_connections"] == 19  # 9 + 10
        assert data["avg_utilization"] > 0

    @pytest.mark.asyncio
    async def test_get_pool_stats_summary_empty(
        self, renderer: MagicMock, pool_manager: MagicMock
    ) -> None:
        pool_manager.get_stats.return_value = {}
        controller = PoolHealthController(
            renderer=renderer, pool_manager=pool_manager
        )
        resp = await controller.get_pool_stats_summary(_mock_request())
        assert resp.status_code == 200
        data = loads(resp.body)
        assert data["avg_utilization"] == 0.0

    # -- get_prometheus_metrics --

    @pytest.mark.asyncio
    async def test_get_prometheus_metrics(
        self, controller: PoolHealthController
    ) -> None:
        resp = await controller.get_prometheus_metrics(_mock_request())
        assert resp.status_code == 200
        body = resp.body.decode()
        assert "pool_active_connections" in body
        assert "pool_utilization" in body
        assert resp.media_type == "text/plain; version=0.0.4"

    @pytest.mark.asyncio
    async def test_get_prometheus_metrics_503(
        self, controller_no_pm: PoolHealthController
    ) -> None:
        resp = await controller_no_pm.get_prometheus_metrics(_mock_request())
        assert resp.status_code == 503

    # -- get_json_metrics --

    @pytest.mark.asyncio
    async def test_get_json_metrics(
        self, controller: PoolHealthController
    ) -> None:
        resp = await controller.get_json_metrics(_mock_request())
        assert resp.status_code == 200
        data = loads(resp.body)
        assert "main" in data
        assert "secondary" in data

    @pytest.mark.asyncio
    async def test_get_json_metrics_503(
        self, controller_no_pm: PoolHealthController
    ) -> None:
        resp = await controller_no_pm.get_json_metrics(_mock_request())
        assert resp.status_code == 503
