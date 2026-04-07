from __future__ import annotations


class _Collector:
    def __init__(self) -> None:
        self.calls: list[tuple[str, float, dict[str, str]]] = []

    def increment(self, name: str, value: float = 1.0, tags: dict[str, str] | None = None) -> None:
        self.calls.append((name, value, tags or {}))

    def histogram(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        self.calls.append((name, value, tags or {}))


def test_admin_metrics_records_list_operation() -> None:
    from lexigram.admin.observability.admin_metrics import AdminMetrics

    collector = _Collector()
    metrics = AdminMetrics(collector=collector)
    metrics.record_operation("list", resource="users", status="success", duration_seconds=0.12)

    assert ("admin_operations_total", 1.0, {"operation": "list", "resource": "users", "status": "success"}) in collector.calls
    assert ("admin_operation_duration_seconds", 0.12, {"operation": "list", "resource": "users", "status": "success"}) in collector.calls


def test_admin_metrics_omits_user_id_label() -> None:
    from lexigram.admin.observability.admin_metrics import AdminMetrics

    collector = _Collector()
    metrics = AdminMetrics(collector=collector)
    metrics.record_authz_denied(resource="users", user_id="u123")
    assert all("user_id" not in labels for _, _, labels in collector.calls)
