"""Pool Health Controller for monitoring connection pools.

Provides HTTP endpoints for checking pool health, viewing statistics,
and managing connection pools in the admin interface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.controllers.base import AdminController
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.admin.auth.protocols import AdminAuditLogServiceProtocol
    from lexigram.admin.engine.renderer import AdminRenderer
    from lexigram.contracts.core import TaskManagerProtocol
    from lexigram.contracts.infra import PoolManagerProtocol
from lexigram.di.decorators import inject

logger = get_logger(__name__)

_POOL_HEALTH_VIEW_PERMISSION = "pool_health.view"
_POOL_HEALTH_MANAGE_PERMISSION = "pool_health.manage"


@inject
class PoolHealthController(AdminController):
    """Controller for connection pool health monitoring.

    Routes:
    - GET /admin/pools/health - Get health status for all pools
    - GET /admin/pools/health/{name} - Get health for specific pool
    - POST /admin/pools/{name}/reconnect - Force reconnect a pool
    """

    def __init__(
        self,
        renderer: AdminRenderer | None = None,
        pool_manager: PoolManagerProtocol | None = None,
        task_manager: TaskManagerProtocol | None = None,
        audit_service: AdminAuditLogServiceProtocol | None = None,
    ) -> None:
        """Initialize the pool health controller.

        Args:
            renderer: AdminRenderer instance (DI-injected, optional).
            pool_manager: PoolManager instance for querying pool state (optional).
            task_manager: TaskManagerProtocol instance (optional).
            audit_service: Security audit log service (optional; denials are
                best-effort logged, failures never break the response path).
        """
        if renderer is None:
            from lexigram.admin.engine.renderer import AdminRenderer

            renderer = AdminRenderer()
        super().__init__(renderer=renderer, task_manager=task_manager)
        self._pool_manager = pool_manager
        self._audit_service = audit_service

    def _require_pool_manager(self) -> JSONResponse | None:
        """Return a 503 response if no pool manager is available, otherwise None."""
        if self._pool_manager is None:
            return JSONResponse(
                {"error": "Pool manager is not available"},
                status_code=503,
            )
        return None

    @staticmethod
    def _user_permissions(request: Request) -> frozenset[str]:
        """Return the requesting user's permission set (empty when unknown)."""
        user = getattr(getattr(request, "state", None), "user", None)
        return frozenset(getattr(user, "permissions", None) or ())

    @staticmethod
    def _user_is_superadmin(request: Request) -> bool:
        """Return True when the requesting user holds the superadmin role.

        Superadmin bypasses per-spec permission gating so accounts created
        with an empty permission set (e.g. via the setup wizard) can still
        manage system operations.
        """
        user = getattr(getattr(request, "state", None), "user", None)
        roles = getattr(user, "roles", None) or ()
        return "superadmin" in roles

    async def _audit(
        self,
        request: Request,
        success: bool = True,
        event_type: AdminSecurityEventType = AdminSecurityEventType.SETTINGS_UPDATED,
        **metadata: Any,
    ) -> None:
        """Append a security event to the audit log, best-effort."""
        if not self._audit_service:
            return
        try:
            client = getattr(request, "client", None)
            await self._audit_service.log_event(
                event_type=event_type,
                ip_address=getattr(client, "host", "unknown"),
                user_agent=request.headers.get("user-agent", "") or "",
                success=success,
                metadata=metadata,
            )
        except Exception:  # noqa: BLE001 — audit failures must not break the response path
            logger.warning("pool_health.audit_failed", **metadata)

    async def get_all_health(self, request: Request) -> JSONResponse:
        """Get health status for all connection pools."""
        if (missing := self._require_pool_manager()) is not None:
            return missing
        if not self._user_is_superadmin(
            request
        ) and _POOL_HEALTH_VIEW_PERMISSION not in self._user_permissions(request):
            await self._audit(
                request,
                success=False,
                event_type=AdminSecurityEventType.PERMISSION_DENIED,
                controller="pool_health",
                action="get_all_health",
            )
            return JSONResponse({"error": "Permission denied"}, status_code=403)
        try:
            all_stats = self._pool_manager.get_stats()  # type: ignore[union-attr]
            pools_data = {}
            for name, stats in all_stats.items():
                is_healthy = stats.pool_utilization < 90.0
                pools_data[name] = {
                    "name": name,
                    "is_healthy": is_healthy,
                    "stats": stats.__dict__,
                    "last_check": stats.last_health_check,
                    "error": None if is_healthy else "High utilization",
                }

            total = len(pools_data)
            healthy = sum(1 for p in pools_data.values() if p["is_healthy"])

            return JSONResponse(
                {
                    "pools": pools_data,
                    "summary": {
                        "total_pools": total,
                        "healthy_pools": healthy,
                        "unhealthy_pools": total - healthy,
                    },
                },
            )
        except Exception as e:  # noqa: BLE001 — controller boundary; unexpected errors become HTTP 500 responses
            logger.exception("Failed to get all pool health")
            return JSONResponse(
                {"error": "Failed to get pool health", "detail": str(e)},
                status_code=500,
            )

    async def get_pool_health(self, request: Request) -> JSONResponse:
        """Get health status for a specific pool."""
        pool_name = request.path_params.get("name")
        if not pool_name:
            return JSONResponse({"error": "Pool name required"}, status_code=400)
        if (missing := self._require_pool_manager()) is not None:
            return missing
        if not self._user_is_superadmin(
            request
        ) and _POOL_HEALTH_VIEW_PERMISSION not in self._user_permissions(request):
            await self._audit(
                request,
                success=False,
                event_type=AdminSecurityEventType.PERMISSION_DENIED,
                controller="pool_health",
                action="get_pool_health",
            )
            return JSONResponse({"error": "Permission denied"}, status_code=403)
        try:
            pool = await self._pool_manager.get_pool(pool_name)  # type: ignore[union-attr]
            stats = pool.get_stats()
            is_healthy = stats.pool_utilization < 90.0
            return JSONResponse(
                {
                    "name": pool_name,
                    "is_healthy": is_healthy,
                    "stats": stats.__dict__,
                    "last_check": stats.last_health_check,
                    "error": None if is_healthy else "High utilization",
                },
            )
        except KeyError:
            return JSONResponse(
                {"error": f"Pool '{pool_name}' not found"},
                status_code=404,
            )
        except Exception as e:  # noqa: BLE001 — controller boundary; unexpected errors become HTTP 500 responses
            logger.exception("Failed to get health for pool %s", pool_name)
            return JSONResponse(
                {"error": "Failed to get pool health", "detail": str(e)},
                status_code=500,
            )

    async def reconnect_pool(self, request: Request) -> JSONResponse:
        """Force reconnect a specific pool."""
        pool_name = request.path_params.get("name")
        if not pool_name:
            return JSONResponse({"error": "Pool name required"}, status_code=400)
        if (missing := self._require_pool_manager()) is not None:
            return missing
        if not self._user_is_superadmin(
            request
        ) and _POOL_HEALTH_MANAGE_PERMISSION not in self._user_permissions(request):
            await self._audit(
                request,
                success=False,
                event_type=AdminSecurityEventType.PERMISSION_DENIED,
                controller="pool_health",
                action="reconnect_pool",
            )
            return JSONResponse({"error": "Permission denied"}, status_code=403)
        try:
            pool = await self._pool_manager.get_pool(pool_name)  # type: ignore[union-attr]
            await pool.close()
            return JSONResponse(
                {"message": f"Pool '{pool_name}' closed for reconnection"},
            )
        except KeyError:
            return JSONResponse(
                {"error": f"Pool '{pool_name}' not found"},
                status_code=404,
            )
        except Exception as e:  # noqa: BLE001 — controller boundary; unexpected errors become HTTP 500 responses
            logger.exception("Failed to reconnect pool %s", pool_name)
            return JSONResponse(
                {"error": "Failed to reconnect pool", "detail": str(e)},
                status_code=500,
            )

    async def get_pool_stats_summary(self, request: Request) -> JSONResponse:
        """Get aggregated statistics across all pools."""
        if (missing := self._require_pool_manager()) is not None:
            return missing
        if not self._user_is_superadmin(
            request
        ) and _POOL_HEALTH_VIEW_PERMISSION not in self._user_permissions(request):
            await self._audit(
                request,
                success=False,
                event_type=AdminSecurityEventType.PERMISSION_DENIED,
                controller="pool_health",
                action="get_pool_stats_summary",
            )
            return JSONResponse({"error": "Permission denied"}, status_code=403)
        try:
            all_stats = self._pool_manager.get_stats()  # type: ignore[union-attr]
            total_connections = sum(s.total_connections for s in all_stats.values())
            active_connections = sum(s.active_connections for s in all_stats.values())
            idle_connections = sum(s.idle_connections for s in all_stats.values())
            total_created = sum(s.created_connections for s in all_stats.values())
            total_destroyed = sum(s.destroyed_connections for s in all_stats.values())

            utilizations = [s.pool_utilization for s in all_stats.values()]
            avg_utilization = (
                sum(utilizations) / len(utilizations) if utilizations else 0.0
            )
            max_utilization = max(utilizations) if utilizations else 0.0

            return JSONResponse(
                {
                    "total_connections": total_connections,
                    "active_connections": active_connections,
                    "idle_connections": idle_connections,
                    "total_created": total_created,
                    "total_destroyed": total_destroyed,
                    "avg_utilization": avg_utilization,
                    "max_utilization": max_utilization,
                },
            )
        except Exception as e:  # noqa: BLE001 — controller boundary; unexpected errors become HTTP 500 responses
            logger.exception("Failed to compute pool stats summary")
            return JSONResponse(
                {"error": "Failed to get pool stats", "detail": str(e)},
                status_code=500,
            )

    async def get_prometheus_metrics(self, request: Request) -> Response:
        """Export pool metrics in Prometheus format."""
        if (missing := self._require_pool_manager()) is not None:
            return missing
        if not self._user_is_superadmin(
            request
        ) and _POOL_HEALTH_VIEW_PERMISSION not in self._user_permissions(request):
            await self._audit(
                request,
                success=False,
                event_type=AdminSecurityEventType.PERMISSION_DENIED,
                controller="pool_health",
                action="get_prometheus_metrics",
            )
            return JSONResponse({"error": "Permission denied"}, status_code=403)
        try:
            all_stats = self._pool_manager.get_stats()  # type: ignore[union-attr]
            lines = []
            for name, stats in all_stats.items():
                labels = f'pool="{name}"'
                lines.append(
                    f"pool_active_connections{{{labels}}} {stats.active_connections}",
                )
                lines.append(
                    f"pool_total_connections{{{labels}}} {stats.total_connections}",
                )
                lines.append(f"pool_utilization{{{labels}}} {stats.pool_utilization}")

            return Response(
                "\n".join(lines) + "\n",
                media_type="text/plain; version=0.0.4",
            )
        except Exception as e:  # noqa: BLE001 — controller boundary; unexpected errors become HTTP 500 responses
            logger.exception("Failed to export metrics")
            return JSONResponse(
                {"error": "Failed to export metrics", "detail": str(e)},
                status_code=500,
            )

    async def get_json_metrics(self, request: Request) -> JSONResponse:
        """Export pool metrics in JSON format."""
        if (missing := self._require_pool_manager()) is not None:
            return missing
        if not self._user_is_superadmin(
            request
        ) and _POOL_HEALTH_VIEW_PERMISSION not in self._user_permissions(request):
            await self._audit(
                request,
                success=False,
                event_type=AdminSecurityEventType.PERMISSION_DENIED,
                controller="pool_health",
                action="get_json_metrics",
            )
            return JSONResponse({"error": "Permission denied"}, status_code=403)
        try:
            all_stats = self._pool_manager.get_stats()  # type: ignore[union-attr]
            metrics_json = {name: stats.__dict__ for name, stats in all_stats.items()}
            return JSONResponse(metrics_json)
        except Exception as e:  # noqa: BLE001 — controller boundary; unexpected errors become HTTP 500 responses
            logger.exception("Failed to export metrics as JSON")
            return JSONResponse(
                {"error": "Failed to export metrics", "detail": str(e)},
                status_code=500,
            )
