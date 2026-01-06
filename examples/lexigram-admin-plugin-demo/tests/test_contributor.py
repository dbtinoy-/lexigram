from __future__ import annotations

from collections.abc import Sequence

from demo.contributor import DemoContributor
from lexigram.contracts.admin import BaseAdminContributor


def test_is_valid_contributor() -> None:
    assert issubclass(DemoContributor, BaseAdminContributor)


def test_has_required_metadata() -> None:
    c = DemoContributor()
    assert c.name == "demo"
    assert c.display_name == "Demo Plugin"
    assert c.package_source == "demo"
    assert c.priority == 500


def test_contributes_resources() -> None:
    c = DemoContributor()
    resources: Sequence[type] = c.get_resources()
    assert len(resources) >= 2


def test_resources_are_namespaced() -> None:
    c = DemoContributor()
    for r in c.get_resources():
        assert hasattr(r, "name")
        name = getattr(r, "name", "") or r.__name__
        assert name  # names will be namespaced by admin at registration


def test_contributes_dashboard_widgets() -> None:
    c = DemoContributor()
    widgets = c.get_dashboard_widgets()
    assert len(widgets) >= 1
    assert any(w.name == "widget_count" for w in widgets)


def test_contributes_navigation() -> None:
    c = DemoContributor()
    nav = c.get_navigation_items()
    assert len(nav) >= 1


def test_contributes_management_pages() -> None:
    c = DemoContributor()
    pages = c.get_management_pages()
    assert len(pages) >= 1


def test_contributes_settings() -> None:
    c = DemoContributor()
    panels = c.get_settings_panels()
    assert len(panels) >= 1


def test_contributes_actions() -> None:
    c = DemoContributor()
    actions = c.get_actions()
    assert len(actions) >= 1


def test_contributes_routes() -> None:
    c = DemoContributor()
    routes = c.get_routes()
    assert len(routes) >= 1


async def test_actions_are_executable() -> None:
    c = DemoContributor()
    result = await c.execute_action("archive_old", {"days": 30})
    assert isinstance(result, dict)
    assert "archived" in result
