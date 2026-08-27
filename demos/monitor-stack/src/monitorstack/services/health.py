"""Health checker — performs health checks on the service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class HealthStatus(str, Enum):
    """Health status values."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    component: str
    status: HealthStatus
    message: str = ""
    timestamp: str = ""
    details: dict[str, Any] | None = None


class HealthChecker:
    """Performs health checks on the service.

    Demonstrates health check patterns with dependencies.
    """

    def __init__(self, metrics: Any) -> None:
        self._metrics = metrics
        self._checks: dict[str, Any] = {}

    def register_check(self, name: str, check_fn: Any) -> None:
        """Register a health check function."""
        self._checks[name] = check_fn

    async def check_health(self) -> dict[str, Any]:
        """Run all registered health checks."""
        results = []
        overall_status = HealthStatus.HEALTHY

        for name, check_fn in self._checks.items():
            try:
                result = await check_fn()
                results.append(result)
                if result.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
            except Exception as e:
                results.append(HealthCheckResult(
                    component=name,
                    status=HealthStatus.UNHEALTHY,
                    message=str(e),
                    timestamp=datetime.now(UTC).isoformat(),
                ))
                overall_status = HealthStatus.UNHEALTHY

        self._metrics.increment("health_checks_total")
        return {
            "status": overall_status.value,
            "timestamp": datetime.now(UTC).isoformat(),
            "checks": [
                {
                    "component": r.component,
                    "status": r.status.value,
                    "message": r.message,
                    "details": r.details,
                }
                for r in results
            ],
        }

    async def check_self(self) -> HealthCheckResult:
        """Self health check — always returns healthy."""
        return HealthCheckResult(
            component="self",
            status=HealthStatus.HEALTHY,
            message="Service is running",
            timestamp=datetime.now(UTC).isoformat(),
        )
