from __future__ import annotations

from demo.contributor import DemoContributor
from demo.resources.audit_log import AuditLogResource
from demo.resources.widget import WidgetResource


def test_resources_are_returned() -> None:
    c = DemoContributor()
    resources = list(c.get_resources())
    assert len(resources) == 2
    assert WidgetResource in resources
    assert AuditLogResource in resources


def test_widget_resource_has_correct_attributes() -> None:
    assert WidgetResource.name == "widgets"
    assert WidgetResource.cluster == "plugins"
    assert WidgetResource.icon == "box"


def test_audit_log_resource_has_correct_attributes() -> None:
    assert AuditLogResource.name == "audit_logs"
    assert AuditLogResource.cluster == "plugins"
    assert AuditLogResource.icon == "file-text"


def test_widget_resource_has_fields() -> None:
    assert len(WidgetResource.fields) >= 3
    names = {f.name for f in WidgetResource.fields}
    assert "title" in names
    assert "status" in names
    assert "created_at" in names


def test_audit_log_resource_has_fields() -> None:
    assert len(AuditLogResource.fields) >= 3
    names = {f.name for f in AuditLogResource.fields}
    assert "action" in names
    assert "severity" in names
    assert "timestamp" in names


def test_widget_resource_has_search_fields() -> None:
    assert WidgetResource.search_fields == ["title"]


def test_audit_log_resource_has_search_fields() -> None:
    assert AuditLogResource.search_fields == ["action", "user", "target"]
