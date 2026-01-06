from __future__ import annotations

from time import perf_counter
from typing import Any


class AdminMetrics:
    def __init__(self, collector: Any | None = None, enabled: bool = True) -> None:
        self._collector = collector
        self._enabled = enabled

    def record_operation(
        self,
        operation: str,
        *,
        resource: str,
        status: str,
        duration_seconds: float,
    ) -> None:
        if not self._enabled or self._collector is None:
            return
        labels = {"operation": operation, "resource": resource, "status": status}
        self._collector.increment("admin_operations_total", 1.0, labels)
        self._collector.histogram(
            "admin_operation_duration_seconds", duration_seconds, labels
        )

    def record_login(self, *, status: str) -> None:
        if self._enabled and self._collector is not None:
            self._collector.increment("admin_login_total", 1.0, {"status": status})

    def record_authz_denied(self, *, resource: str, user_id: str | None = None) -> None:
        if self._enabled and self._collector is not None:
            self._collector.increment(
                "admin_authz_denied_total", 1.0, {"resource": resource}
            )


class OperationTimer:
    def __init__(self) -> None:
        self._start = perf_counter()

    def elapsed(self) -> float:
        return perf_counter() - self._start
