"""Health route tests (Relay Gateway plan reviewer task: health endpoint).

Covers ``GET /health`` aggregation: check entries per dependency,
aggregate ``ok``/``degraded``/``down`` mapping, HTTP status signaling
(200 vs 503), version and timestamp reporting, and the resolver-missing
degrade path.  Endpoints are exercised with a minimal request double
matching the ``test_web.py`` pattern.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from starlette.responses import JSONResponse

from lexigram.ai.relay.gateway.web.routes.builder import build_routes
from lexigram.ai.relay.gateway.web.routes.health import HEALTH_ROUTE_PATH
from lexigram.contracts.ai.relay import (
    RelayChannelHealth,
    RelayFormat,
    RelayGatewayError,
    RelayRegistryDiagnostics,
)
from lexigram.serialization import loads


class _SnapshotBuilder:
    """Helper building channel health snapshots compactly."""

    @staticmethod
    def snapshot(
        name: str,
        status: str,
        latency_ms: float | None = None,
    ) -> RelayChannelHealth:
        return RelayChannelHealth(
            channel=name,
            target=RelayFormat.OPENAI_CHAT,
            status=status,
            model_count=1,
            latency_ms_p50=latency_ms,
            latency_ms_p95=latency_ms,
            failure_count=0,
            checked_at=datetime.now(UTC),
            detail_code=None,
        )


class FakeHealthService:
    """Duck-typed ``RelayHealthService`` double with canned snapshots."""

    def __init__(
        self,
        snapshots: list[RelayChannelHealth] | None = None,
        *,
        registry_error: RelayGatewayError | None = None,
    ) -> None:
        self._snapshots = snapshots if snapshots is not None else []
        self._registry_error = registry_error

    async def channel_health(self) -> list[RelayChannelHealth]:
        """Return the canned channel snapshots."""
        return self._snapshots

    async def registry_diagnostics(self) -> RelayRegistryDiagnostics:
        """Return diagnostics or raise the canned registry error."""
        if self._registry_error is not None:
            raise self._registry_error
        return RelayRegistryDiagnostics(
            converter_id="relay-converter",
            converter_version="1",
            mapper_ids=(),
            supported_routes=(),
        )


class FakeRequest:
    """Minimal request double matching the health endpoint surface."""

    def __init__(self) -> None:
        self.state = type(
            "State",
            (),
            {"request_id": None, "user": None, "container": None},
        )()


class FakeResolver:
    """Async callable returning the canned health service or ``None``."""

    def __init__(self, service: FakeHealthService | None) -> None:
        self._service = service

    async def __call__(self, request: Any) -> FakeHealthService | None:
        return self._service


def _route(service: FakeHealthService | None) -> Any:
    return next(
        route
        for route in build_routes(
            lambda _request: _FakeGateway(),
            resolve_health=FakeResolver(service),
        )
        if route.path == HEALTH_ROUTE_PATH
    )


class _FakeGateway:
    async def handle(self, request: Any) -> Any:
        raise AssertionError("health route must not dispatch relay requests")


async def _load(response: Any) -> dict[str, Any]:
    assert isinstance(response, JSONResponse)
    return loads(response.body)


class TestHealthAggregation:
    """Aggregate status mapping and HTTP signaling."""

    async def test_all_healthy_reports_ok(self) -> None:
        service = FakeHealthService(
            snapshots=[
                _SnapshotBuilder.snapshot("a", "healthy", 12.4),
                _SnapshotBuilder.snapshot("b", "healthy", None),
            ]
        )
        response = await _route(service).endpoint(FakeRequest())
        assert response.status_code == 200
        payload = await _load(response)
        assert payload["status"] == "ok"
        assert payload["version"]
        assert isinstance(payload["timestamp"], str)
        datetime.fromisoformat(payload["timestamp"])
        assert payload["checks"][0]["name"] == "registry"
        assert payload["checks"][0]["status"] == "ok"
        assert isinstance(payload["checks"][0]["latency_ms"], int)
        assert payload["checks"][0]["latency_ms"] >= 0
        assert payload["checks"][1:] == [
            {"name": "a", "status": "ok", "latency_ms": 12},
            {"name": "b", "status": "ok"},
        ]

    async def test_degraded_channel_reports_degraded_with_200(self) -> None:
        service = FakeHealthService(
            snapshots=[_SnapshotBuilder.snapshot("a", "degraded", 300.0)]
        )
        response = await _route(service).endpoint(FakeRequest())
        assert response.status_code == 200
        assert (await _load(response))["status"] == "degraded"

    async def test_failed_channel_reports_down_with_503(self) -> None:
        for status in ("unavailable", "failed"):
            service = FakeHealthService(
                snapshots=[_SnapshotBuilder.snapshot("a", status)]
            )
            response = await _route(service).endpoint(FakeRequest())
            assert response.status_code == 503
            assert (await _load(response))["status"] == "down"

    async def test_registry_dependency_missing_reports_down(self) -> None:
        service = FakeHealthService(
            registry_error=RelayGatewayError(
                code="DEPENDENCY_UNAVAILABLE",
                message="converter registry is not registered",
                status_code=503,
                request_id="",
            )
        )
        response = await _route(service).endpoint(FakeRequest())
        assert response.status_code == 503
        assert (await _load(response))["status"] == "down"

    async def test_down_wins_over_degraded(self) -> None:
        service = FakeHealthService(
            snapshots=[
                _SnapshotBuilder.snapshot("a", "degraded", 300.0),
                _SnapshotBuilder.snapshot("b", "failed"),
            ]
        )
        response = await _route(service).endpoint(FakeRequest())
        assert response.status_code == 503
        assert (await _load(response))["status"] == "down"

    async def test_empty_channels_reports_ok_from_registry_only(self) -> None:
        service = FakeHealthService()
        response = await _route(service).endpoint(FakeRequest())
        assert response.status_code == 200
        payload = await _load(response)
        assert payload["status"] == "ok"
        assert [check["name"] for check in payload["checks"]] == ["registry"]


class TestHealthResolver:
    """Resolver and mounting behavior."""

    async def test_unresolved_health_service_reports_down_empty(self) -> None:
        response = await _route(None).endpoint(FakeRequest())
        assert response.status_code == 503
        payload = await _load(response)
        assert payload["status"] == "down"
        assert payload["checks"] == []
        assert payload["version"]

    async def test_health_route_absent_without_resolver(self) -> None:
        routes = build_routes(lambda _request: _FakeGateway())
        assert all(route.path != HEALTH_ROUTE_PATH for route in routes)

    async def test_health_route_is_get_and_last(self) -> None:
        routes = build_routes(
            lambda _request: _FakeGateway(),
            resolve_health=FakeResolver(FakeHealthService()),
        )
        route = next(route for route in routes if route.path == HEALTH_ROUTE_PATH)
        assert sorted(route.methods or []) == ["GET", "HEAD"]
        assert routes[-1].path == HEALTH_ROUTE_PATH

    async def test_mount_registers_health_once(self) -> None:
        from types import SimpleNamespace

        from lexigram.ai.relay.gateway.web.contributor import (
            RelayGatewayWebContributor,
        )

        app = type(
            "FakeApp",
            (),
            {"routes": [], "registrations": [], "add_route": _record_mount},
        )()
        contributor = RelayGatewayWebContributor()
        await contributor.mount_to_app(app, SimpleNamespace())
        count = sum(1 for path, _, _ in app.registrations if path == "/health")
        assert count == 1
        health_methods = [
            methods
            for path, _, methods in app.registrations
            if path == "/health"
        ]
        assert health_methods == [["GET", "HEAD"]]


def _record_mount(app: Any, path: str, endpoint: Any, methods: list[str] | None) -> None:
    app.registrations.append((path, endpoint, methods))
    app.routes.append(type("FakeRoute", (), {"path": path})())