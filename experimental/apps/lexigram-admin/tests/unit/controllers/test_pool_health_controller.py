"""Tests for PoolHealthController."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request

from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.controllers.pool_health import (
    _POOL_HEALTH_MANAGE_PERMISSION,
    _POOL_HEALTH_VIEW_PERMISSION,
    PoolHealthController,
)
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
    """Build a minimal Request stub with path_params and a superadmin user."""
    req = MagicMock(spec=Request)
    req.path_params = overrides
    req.state = SimpleNamespace(
        user=SimpleNamespace(roles=("superadmin",), permissions=frozenset())
    )
    return req


def _user_request(
    *,
    roles: tuple[str, ...] = (),
    permissions: frozenset[str] = frozenset(),
    name: str | None = None,
) -> Request:
    """Build a Request stub carrying an explicit user identity."""
    req = MagicMock(spec=Request)
    req.path_params = {"name": name} if name else {}
    req.state = SimpleNamespace(
        user=SimpleNamespace(roles=roles, permissions=permissions)
    )
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
    async def test_get_all_health(self, controller: PoolHealthController) -> None:
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
        controller = PoolHealthController(renderer=renderer, pool_manager=pool_manager)
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
        resp = await controller_no_pm.get_pool_health(_mock_request(name="main"))
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
        controller = PoolHealthController(renderer=renderer, pool_manager=pool_manager)
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
    async def test_get_json_metrics(self, controller: PoolHealthController) -> None:
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


class TestPoolHealthPermissions:
    """Tests for the permission helpers and endpoint gates."""

    def test_user_permissions_empty_when_absent(self) -> None:
        """Missing permissions attribute yields an empty set."""
        req = MagicMock(spec=Request)
        req.state = SimpleNamespace(user=SimpleNamespace(roles=()))
        assert PoolHealthController._user_permissions(req) == frozenset()

    def test_user_permissions_returns_set(self) -> None:
        """Present permissions are returned as a frozenset."""
        req = _user_request(permissions=frozenset({"pool_health.view"}))
        assert PoolHealthController._user_permissions(req) == frozenset(
            {"pool_health.view"}
        )

    def test_user_is_superadmin_true_when_role_present(self) -> None:
        """The superadmin role bypasses the gates."""
        req = _user_request(roles=("superadmin",))
        controller = PoolHealthController(renderer=MagicMock(), pool_manager=MagicMock())
        assert controller._user_is_superadmin(req) is True

    def test_user_is_superadmin_false_without_role(self) -> None:
        """A regular role does not bypass the gates."""
        req = _user_request(roles=("operator",))
        controller = PoolHealthController(renderer=MagicMock(), pool_manager=MagicMock())
        assert controller._user_is_superadmin(req) is False

    @pytest.fixture
    def audit_service(self) -> AsyncMock:
        return AsyncMock()

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
        }
        pm.get_pool = AsyncMock()
        return pm

    @pytest.fixture
    def controller(
        self,
        renderer: MagicMock,
        pool_manager: MagicMock,
        audit_service: AsyncMock,
    ) -> PoolHealthController:
        return PoolHealthController(
            renderer=renderer,
            pool_manager=pool_manager,
            audit_service=audit_service,
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "endpoint, kwargs",
        [
            ("get_all_health", {}),
            ("get_pool_health", {"name": "main"}),
            ("get_pool_stats_summary", {}),
            ("get_prometheus_metrics", {}),
            ("get_json_metrics", {}),
        ],
    )
    async def test_read_endpoints_denied_without_permission(
        self,
        controller: PoolHealthController,
        endpoint: str,
        kwargs: dict[str, str],
    ) -> None:
        """Non-superadmin without the view permission gets 403 on reads."""
        resp = await getattr(controller, endpoint)(
            _user_request(roles=("operator",), **kwargs)
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_reconnect_denied_without_permission(
        self, controller: PoolHealthController
    ) -> None:
        """Non-superadmin without the manage permission gets 403."""
        resp = await controller.reconnect_pool(
            _user_request(roles=("operator",), name="main")
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "endpoint, kwargs",
        [
            ("get_all_health", {}),
            ("get_pool_health", {"name": "main"}),
            ("get_pool_stats_summary", {}),
            ("get_prometheus_metrics", {}),
            ("get_json_metrics", {}),
        ],
    )
    async def test_read_endpoints_allowed_with_view_permission(
        self,
        controller: PoolHealthController,
        pool_manager: MagicMock,
        endpoint: str,
        kwargs: dict[str, str],
    ) -> None:
        """The view permission grants reads (but not reconnects)."""
        pool = MagicMock()
        pool.get_stats.return_value = _FakeStats(pool_utilization=30.0)
        pool_manager.get_pool = AsyncMock(return_value=pool)
        resp = await getattr(controller, endpoint)(
            _user_request(
                roles=("operator",),
                permissions=frozenset({_POOL_HEALTH_VIEW_PERMISSION}),
                **kwargs,
            )
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_view_permission_does_not_grant_reconnect(
        self, controller: PoolHealthController, pool_manager: MagicMock
    ) -> None:
        """view is not manage — reconnect stays denied."""
        resp = await controller.reconnect_pool(
            _user_request(
                roles=("operator",),
                permissions=frozenset({_POOL_HEALTH_VIEW_PERMISSION}),
                name="main",
            )
        )
        assert resp.status_code == 403
        pool_manager.get_pool.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_manage_permission_grants_reconnect(
        self, controller: PoolHealthController, pool_manager: MagicMock
    ) -> None:
        """The manage permission grants the destructive action."""
        pool = MagicMock()
        pool.close = AsyncMock()
        pool_manager.get_pool = AsyncMock(return_value=pool)
        resp = await controller.reconnect_pool(
            _user_request(
                roles=("operator",),
                permissions=frozenset({_POOL_HEALTH_MANAGE_PERMISSION}),
                name="main",
            )
        )
        assert resp.status_code == 200
        pool.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_superadmin_bypasses_with_empty_permissions(
        self, controller: PoolHealthController, pool_manager: MagicMock
    ) -> None:
        """Superadmin with an empty permission set passes every gate."""
        pool = MagicMock()
        pool.close = AsyncMock()
        pool_manager.get_pool = AsyncMock(return_value=pool)

        assert (
            await controller.get_all_health(_user_request(roles=("superadmin",)))
        ).status_code == 200
        assert (
            await controller.reconnect_pool(
                _user_request(roles=("superadmin",), name="main")
            )
        ).status_code == 200

    @pytest.mark.asyncio
    async def test_denial_is_audited(
        self, controller: PoolHealthController, audit_service: AsyncMock
    ) -> None:
        """Denials log a PERMISSION_DENIED event with the action metadata."""
        resp = await controller.get_all_health(_user_request(roles=("operator",)))
        assert resp.status_code == 403
        audit_service.log_event.assert_awaited_once()
        call_kwargs = audit_service.log_event.await_args.kwargs
        assert call_kwargs["event_type"] == AdminSecurityEventType.PERMISSION_DENIED
        assert call_kwargs["metadata"]["action"] == "get_all_health"
        assert call_kwargs["success"] is False

    @pytest.mark.asyncio
    async def test_audit_failure_does_not_break_response(
        self,
        renderer: MagicMock,
        pool_manager: MagicMock,
        audit_service: AsyncMock,
    ) -> None:
        """A raising audit service still yields 403, never an exception."""
        audit_service.log_event = AsyncMock(side_effect=RuntimeError("boom"))
        controller = PoolHealthController(
            renderer=renderer,
            pool_manager=pool_manager,
            audit_service=audit_service,
        )
        resp = await controller.get_all_health(_user_request(roles=("operator",)))
        assert resp.status_code == 403
