"""Pool Health Controller for monitoring connection pools.

Provides HTTP endpoints for checking pool health, viewing statistics,
and managing connection pools in the admin interface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from lexigram.admin.controllers.base import AdminController
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.admin.engine.renderer import AdminRenderer
    from lexigram.contracts.core import TaskManagerProtocol
    from lexigram.contracts.infra import PoolManagerProtocol
from lexigram.di.decorators import inject

logger = get_logger(__name__)


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
    ) -> None:
        """Initialize the pool health controller.

        Args:
            renderer: AdminRenderer instance (DI-injected, optional).
            pool_manager: PoolManager instance for querying pool state (optional).
            task_manager: TaskManagerProtocol instance (optional).
        """
        super().__init__(renderer=renderer, task_manager=task_manager)
        self._pool_manager = pool_manager

    def _require_pool_manager(self) -> JSONResponse | None:
        """Return a 503 response if no pool manager is available, otherwise None."""
        if self._pool_manager is None:
            return JSONResponse(
                {"error": "Pool manager is not available"},
                status_code=503,
            )
        return None

    async def get_all_health(self, request: Request) -> JSONResponse:
        """Get health status for all connection pools."""
        if (missing := self._require_pool_manager()) is not None:
            return missing
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
