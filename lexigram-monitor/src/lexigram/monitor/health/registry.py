from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
import time
from typing import Any

from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.logging import get_logger
from lexigram.monitor.health.base import HealthCheck
from lexigram.primitives.registry import Registry

logger = get_logger(__name__)


class HealthCheckRegistry(Registry[str, HealthCheck]):
    """Registry for managing health checks.

    Extends :class:`Registry` for unified introspection.  Sidecar lists
    track which checks participate in liveness vs readiness probes.
    """

    def __init__(self) -> None:
        super().__init__(name="health.checks", allow_overwrite=True)
        self._liveness_checks: list[str] = []
        self._readiness_checks: list[str] = []

    def _register(
        self,
        check: HealthCheck,
        liveness: bool = True,
        readiness: bool = True,
    ) -> None:
        super().register(check.name, check)
        if liveness and check.name not in self._liveness_checks:
            self._liveness_checks.append(check.name)
        if readiness and check.name not in self._readiness_checks:
            self._readiness_checks.append(check.name)

    def _register_function(
        self,
        name: str,
        func: Callable,
        critical: bool = True,
        liveness: bool = True,
        readiness: bool = True,
    ) -> None:
        from lexigram.monitor.health.functions import FunctionHealthCheck

        check = FunctionHealthCheck(name, func, critical)
        self._register(check, liveness, readiness)

    async def _check_liveness(self) -> dict[str, Any]:
        results = []
        overall_status = HealthStatus.HEALTHY

        for check_name in self._liveness_checks:
            check = self.get(check_name)
            if not check:
                continue

            try:
                start = time.time()
                result = await check.check()
                result = replace(result, duration_ms=(time.time() - start) * 1000)
                results.append(result)

                if result.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY

            except (OSError, ConnectionError, RuntimeError, ValueError) as e:
                logger.exception("Liveness check %s error", check_name)
                result = HealthCheckResult(
                    component=check_name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check failed: {e}",
                )
                results.append(result)
                overall_status = HealthStatus.UNHEALTHY

        return {
            "status": overall_status.value,
            "checks": [r.to_dict() for r in results],
            "timestamp": time.time(),
        }

    async def _check_readiness(self) -> dict[str, Any]:
        results = []
        overall_status = HealthStatus.HEALTHY

        for check_name in self._readiness_checks:
            check = self.get(check_name)
            if not check:
                continue

            try:
                start = time.time()
                result = await check.check()
                result = replace(result, duration_ms=(time.time() - start) * 1000)
                results.append(result)

                if check.critical and result.status != HealthStatus.HEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif (
                    result.status != HealthStatus.HEALTHY
                    and overall_status == HealthStatus.HEALTHY
                ):
                    overall_status = HealthStatus.DEGRADED

            except (OSError, ConnectionError, RuntimeError, ValueError) as e:
                logger.exception("Readiness check %s error", check_name)
                result = HealthCheckResult(
                    component=check_name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check failed: {e}",
                )
                results.append(result)
                if check.critical:
                    overall_status = HealthStatus.UNHEALTHY
                elif overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED

        return {
            "status": overall_status.value,
            "checks": [r.to_dict() for r in results],
            "timestamp": time.time(),
        }

    # --- HealthCheckRegistryProtocol Compliance ---

    def add(
        self,
        name: str,
        check: Callable[[], Any],
        *,
        timeout: float | None = None,
        critical: bool = True,
        category: Any = None,
    ) -> None:
        """Add a health check to satisfy HealthCheckRegistryProtocol."""
        is_liveness = (
            "liveness" in str(category).lower() or "startup" in str(category).lower()
        )
        is_readiness = "readiness" in str(category).lower() or category is None
        self._register_function(
            name,
            check,
            critical=critical,
            liveness=is_liveness,
            readiness=is_readiness,
        )

    async def run_all(self) -> tuple[Any, dict[str, Any]]:
        l_res = await self._check_liveness()
        r_res = await self._check_readiness()

        status = HealthStatus.HEALTHY
        if (
            l_res["status"] == HealthStatus.UNHEALTHY.value
            or r_res["status"] == HealthStatus.UNHEALTHY.value
        ):
            status = HealthStatus.UNHEALTHY
        elif (
            l_res["status"] == HealthStatus.DEGRADED.value
            or r_res["status"] == HealthStatus.DEGRADED.value
        ):
            status = HealthStatus.DEGRADED

        return status, {"liveness": l_res, "readiness": r_res}

    async def run_liveness(self) -> tuple[Any, dict[str, Any]]:
        res = await self._check_liveness()
        try:
            status = HealthStatus(res["status"])
        except ValueError:
            status = HealthStatus.UNKNOWN
        return status, res

    async def run_readiness(self) -> tuple[Any, dict[str, Any]]:
        res = await self._check_readiness()
        try:
            status = HealthStatus(res["status"])
        except ValueError:
            status = HealthStatus.UNKNOWN
        return status, res

    async def run_startup(self) -> tuple[Any, dict[str, Any]]:
        return await self.run_liveness()

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Satisfy HealthCheckProtocol."""
        status_val, details = await self.run_all()
        return HealthCheckResult(
            component="health_registry",
            status=status_val,
            details=details,
        )
