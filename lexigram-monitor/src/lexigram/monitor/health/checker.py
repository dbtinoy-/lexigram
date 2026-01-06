"""Health checking utilities for Lexigram Framework."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import TYPE_CHECKING, Any

from lexigram.contracts.core.health import (
    HealthCheckCategory,
    HealthCheckProtocol,
    HealthCheckResult,
    HealthStatus,
)

if TYPE_CHECKING:
    from collections.abc import Callable

_HEALTH_CHECK_ATTR = "_health_check_name"


class HealthChecker:
    """Aggregates and runs named health checks with optional per-check timeouts.

    Checks can be tagged with a :class:`~lexigram.contracts.core.health.HealthCheckCategory`
    (``LIVENESS``, ``READINESS``, or ``STARTUP``) and run selectively via
    :meth:`run_liveness`, :meth:`run_readiness`, or :meth:`run_startup`.
    Methods that omit a category default to ``READINESS``.
    """

    def __init__(self) -> None:
        self._checks: dict[str, HealthCheckProtocol | Callable[[], Any]] = {}
        self._timeouts: dict[str, float] = {}
        self._categories: dict[str, HealthCheckCategory] = {}

    def add(
        self,
        name: str,
        check: HealthCheckProtocol | Callable[[], Any],
        *,
        timeout: float | None = None,
        category: HealthCheckCategory = HealthCheckCategory.READINESS,
    ) -> None:
        """Add a named health check with an optional timeout and category.

        Args:
            name: Unique identifier for this check.
            check: A :class:`HealthCheckProtocol` instance or a callable
                returning a health indicator (bool, dict, or
                :class:`HealthCheckResult`).
            timeout: Per-check timeout in seconds. If the check exceeds
                this duration it is reported as UNHEALTHY.
            category: Whether this check is a liveness, readiness, or
                startup check. Defaults to ``READINESS``.
        """
        self._checks[name] = check
        self._categories[name] = category
        if timeout is not None:
            self._timeouts[name] = timeout

    def remove(self, name: str) -> None:
        """Remove a named health check.

        Args:
            name: The check name to remove.

        Raises:
            KeyError: If no check with this name is registered.
        """
        if name not in self._checks:
            msg = f"Health check '{name}' not registered"
            raise KeyError(msg)
        del self._checks[name]
        self._timeouts.pop(name, None)
        self._categories.pop(name, None)

    def has(self, name: str) -> bool:
        """Check whether a health check with the given name is registered.

        Args:
            name: The check name.

        Returns:
            True if the check exists.
        """
        return name in self._checks

    @property
    def check_names(self) -> list[str]:
        """Sorted list of all registered health check names.

        Returns:
            A sorted list of check name strings.
        """
        return sorted(self._checks.keys())

    def register(self, check: Callable[[], Any]) -> None:
        """Register a callable decorated with :func:`health_checker`.

        The check name is read from the ``_health_check_name`` attribute
        stamped by the :func:`health_checker` decorator.

        Args:
            check: A decorated health check callable.

        Raises:
            ValueError: If *check* was not decorated with
                :func:`health_checker`.
        """
        name = getattr(check, _HEALTH_CHECK_ATTR, None)
        if name is None:
            raise ValueError(
                f"{check!r} is not decorated with @health_checker",
            )
        self.add(name, check)

    async def run_all(self) -> dict[str, HealthCheckResult]:
        """Run all health checks and return unified results.

        Per-check timeouts are enforced when configured. Timed-out checks
        are reported as UNHEALTHY.

        Returns:
            A dict mapping check names to their ``HealthCheckResult``.
        """
        results: dict[str, HealthCheckResult] = {}
        for name, check in self._checks.items():
            start_time = asyncio.get_event_loop().time()
            timeout = self._timeouts.get(name)
            try:
                if hasattr(check, "health_check"):
                    coro = check.health_check()
                    if timeout is not None:
                        result = await asyncio.wait_for(coro, timeout=timeout)
                    else:
                        result = await coro
                elif asyncio.iscoroutinefunction(check):
                    coro = check()
                    if timeout is not None:
                        raw_result = await asyncio.wait_for(coro, timeout=timeout)
                    else:
                        raw_result = await coro
                    result = self._map_to_result(name, raw_result)
                else:
                    raw_result = check()
                    result = self._map_to_result(name, raw_result)

                duration = (asyncio.get_event_loop().time() - start_time) * 1000
                if not result.duration_ms:
                    result = replace(result, duration_ms=duration)
                results[name] = result
            except TimeoutError:
                results[name] = HealthCheckResult(
                    component=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check timed out after {timeout}s",
                    duration_ms=(asyncio.get_event_loop().time() - start_time) * 1000,
                )
            except (RuntimeError, OSError, ConnectionError, ValueError, TypeError) as e:
                results[name] = HealthCheckResult(
                    component=name,
                    status=HealthStatus.UNHEALTHY,
                    message=str(e),
                    duration_ms=(asyncio.get_event_loop().time() - start_time) * 1000,
                )
        return results

    def aggregate_status(self, results: dict[str, HealthCheckResult]) -> HealthStatus:
        """Determine the overall health status from individual check results.

        Returns HEALTHY only if every check is HEALTHY. Returns DEGRADED if
        any check is DEGRADED but none are UNHEALTHY. Returns UNHEALTHY
        otherwise.

        Args:
            results: The dict returned by :meth:`run_all`.

        Returns:
            The aggregate ``HealthStatus``.
        """
        if not results:
            return HealthStatus.UNKNOWN
        statuses = {r.status for r in results.values()}
        if statuses == {HealthStatus.HEALTHY}:
            return HealthStatus.HEALTHY
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        return HealthStatus.UNKNOWN

    async def run_all_with_summary(
        self,
    ) -> tuple[HealthStatus, dict[str, HealthCheckResult]]:
        """Run all health checks and return the aggregate status together with details.

        Convenience wrapper that calls :meth:`run_all` and
        :meth:`aggregate_status` in one step.

        Returns:
            A tuple of ``(aggregate_status, per_check_results)``.
        """
        results = await self.run_all()
        return self.aggregate_status(results), results

    async def run_liveness(
        self,
    ) -> tuple[HealthStatus, dict[str, HealthCheckResult]]:
        """Run only LIVENESS checks and return aggregate status and details.

        Returns:
            A tuple of ``(aggregate_status, per_check_results)``.
        """
        return await self._run_by_category(HealthCheckCategory.LIVENESS)

    async def run_readiness(
        self,
    ) -> tuple[HealthStatus, dict[str, HealthCheckResult]]:
        """Run only READINESS checks and return aggregate status and details.

        Returns:
            A tuple of ``(aggregate_status, per_check_results)``.
        """
        return await self._run_by_category(HealthCheckCategory.READINESS)

    async def run_startup(
        self,
    ) -> tuple[HealthStatus, dict[str, HealthCheckResult]]:
        """Run only STARTUP checks and return aggregate status and details.

        Returns:
            A tuple of ``(aggregate_status, per_check_results)``.
        """
        return await self._run_by_category(HealthCheckCategory.STARTUP)

    async def _run_by_category(
        self,
        category: HealthCheckCategory,
    ) -> tuple[HealthStatus, dict[str, HealthCheckResult]]:
        """Run all checks registered under the given category.

        Args:
            category: The HealthCheckCategory to filter on.

        Returns:
            Tuple of ``(aggregate_status, per_check_results)``.
        """
        filtered = {name for name, cat in self._categories.items() if cat == category}
        # Temporarily swap _checks to only run matching ones
        original = self._checks
        self._checks = {k: v for k, v in original.items() if k in filtered}
        try:
            results = await self.run_all()
        finally:
            self._checks = original
        return self.aggregate_status(results), results

    def _map_to_result(self, name: str, raw: Any) -> HealthCheckResult:
        """Map raw result to HealthCheckResult."""
        if isinstance(raw, HealthCheckResult):
            return raw

        if isinstance(raw, dict):
            status_val = raw.get("status", "unknown")
            try:
                status = HealthStatus(status_val)
            except ValueError:
                status = HealthStatus.UNKNOWN

            return HealthCheckResult(
                component=name,
                status=status,
                message=raw.get("message"),
                details={
                    k: v for k, v in raw.items() if k not in ("status", "message")
                },
            )

        return HealthCheckResult(
            component=name,
            status=HealthStatus.HEALTHY if raw else HealthStatus.UNHEALTHY,
        )


def health_checker(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator that marks a callable as a named health check.

    The decorated function can later be registered on a
    :class:`HealthChecker` via :meth:`HealthChecker.register`.

    Args:
        name: Human-readable name for this check (e.g. ``"database"``).

    Example::

        @health_checker("database")
        async def check_db() -> bool:
            return await db.ping()

        checker = HealthChecker()
        checker.register(check_db)
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        setattr(func, _HEALTH_CHECK_ATTR, name)
        return func

    return decorator


__all__ = [
    "HealthCheckCategory",
    "HealthCheckProtocol",
    "HealthCheckResult",
    "HealthChecker",
    "HealthStatus",
    "health_checker",
]
