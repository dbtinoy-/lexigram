"""Health and metrics helpers for the Lexigram cache provider.

These module-level functions are extracted from
:class:`~lexigram.cache.di.provider.CacheProvider` so that ``provider.py``
stays focused on lifecycle management.  They are called by the provider and
are not part of the public API surface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.cache.service.core import CacheService
    from lexigram.cache.service.stampede import StampedeProtectedCache
    from lexigram.contracts import CacheBackendProtocol

logger = get_logger(__name__)


async def get_health_status(
    services: dict[str, CacheService],
    backends: dict[str, CacheBackendProtocol],
) -> HealthCheckResult:
    """Aggregate health across all cache services and backends.

    Args:
        services: Mapping of backend name → CacheService instance.
        backends: Mapping of backend name → CacheBackendProtocol instance.

    Returns:
        Structured :class:`~lexigram.contracts.types.HealthCheckResult` with
        per-service and per-backend detail.
    """
    overall_status = HealthStatus.HEALTHY
    details: dict[str, Any] = {"services": {}, "backends": {}}
    errors: list[str] = []

    # --- Services ---
    for name, service in services.items():
        try:
            try:
                service_status = await service.health_check()
            except TypeError:
                service_status = service.health_check()  # type: ignore[assignment]

            if service_status is not None and hasattr(service_status, "status"):
                status_value = service_status.status
                error_value = getattr(service_status, "error", None)
                if status_value != HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
                    if error_value:
                        errors.append(f"Service {name}: {error_value}")
                service_dict = (
                    service_status.model_dump()
                    if hasattr(service_status, "model_dump")
                    else service_status
                )
            elif isinstance(service_status, dict):
                status_value = service_status.get("status", "unknown")
                error_value = service_status.get("error")
                if status_value != "healthy":
                    overall_status = HealthStatus.DEGRADED
                    if error_value:
                        errors.append(f"Service {name}: {error_value}")
                service_dict = service_status
            else:
                service_dict = {
                    "status": "unknown",
                    "error": "Invalid health check result",
                }

            details["services"][name] = service_dict
        except (ConnectionError, TimeoutError, OSError, RuntimeError) as e:
            details["services"][name] = {"status": "unhealthy", "error": str(e)}
            overall_status = HealthStatus.UNHEALTHY
            errors.append(f"Service {name} check failed: {e}")

    # --- Backends ---
    for name, backend in backends.items():
        try:
            try:
                backend_status = await backend.health_check()
            except TypeError:
                backend_status = backend.health_check()  # type: ignore[assignment]

            if backend_status is not None and hasattr(backend_status, "status"):
                status_value = backend_status.status
                if status_value != HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
                backend_dict = (
                    backend_status.model_dump()
                    if hasattr(backend_status, "model_dump")
                    else backend_status
                )
            elif isinstance(backend_status, dict):
                status_value = backend_status.get("status", "unknown")
                if status_value != "healthy":
                    overall_status = HealthStatus.DEGRADED
                backend_dict = backend_status
            else:
                backend_dict = {"status": "unknown"}

            details["backends"][name] = backend_dict

        except (ConnectionError, TimeoutError, OSError, RuntimeError) as e:
            details["backends"][name] = {"status": "unhealthy", "error": str(e)}
            overall_status = HealthStatus.UNHEALTHY
            errors.append(f"Backend {name} check failed: {e}")

    return HealthCheckResult(
        component="cache:provider",
        status=overall_status,
        details=details,
        error=" | ".join(errors) if errors else None,
    )


async def get_metrics(
    services: dict[str, CacheService],
    backends: dict[str, CacheBackendProtocol],
    protection: StampedeProtectedCache | None,
) -> dict[str, Any]:
    """Collect metrics from all registered cache services.

    Args:
        services: Mapping of backend name → CacheService instance.
        backends: Mapping of backend name → CacheBackendProtocol instance.
        protection: Stampede protection instance, or ``None`` when disabled.

    Returns:
        Metrics dictionary with per-provider summary and per-service stats.
    """
    metrics: dict[str, Any] = {
        "provider": {
            "services_count": len(services),
            "backends_count": len(backends),
            "protection_enabled": protection is not None,
        },
        "services": {},
    }

    for name, service in services.items():
        try:
            service_metrics = service.get_metrics()
            metrics["services"][name] = service_metrics
        except (RuntimeError, OSError, ValueError, TypeError, AttributeError) as e:
            metrics["services"][name] = {"error": str(e)}

    return metrics


__all__ = ["get_health_status", "get_metrics"]
