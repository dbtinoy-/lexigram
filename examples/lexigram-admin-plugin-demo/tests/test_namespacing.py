from __future__ import annotations

from demo.contributor import DemoContributor


def test_resource_names_are_set() -> None:
    c = DemoContributor()
    for r in c.get_resources():
        name = getattr(r, "name", None) or r.__name__
        assert name


def test_widget_contributor_is_set() -> None:
    c = DemoContributor()
    for w in c.get_dashboard_widgets():
        assert w.name
        assert w.contributor == "demo"


def test_page_contributor_is_set() -> None:
    c = DemoContributor()
    for p in c.get_management_pages():
        assert p.name
        assert p.contributor == "demo"


def test_settings_contributor_is_set() -> None:
    c = DemoContributor()
    for s in c.get_settings_panels():
        assert s.name
        assert s.contributor == "demo"


def test_action_contributor_is_set() -> None:
    c = DemoContributor()
    for a in c.get_actions():
        assert a.name
        assert a.contributor == "demo"


def test_action_handlers_are_module_func_format() -> None:
    c = DemoContributor()
    for a in c.get_actions():
        assert ":" in a.handler, (
            f"action '{a.name}' handler '{a.handler}' must be module:func"
        )
        module_path, _, func_name = a.handler.partition(":")
        assert module_path
        assert func_name


def test_route_names_are_set() -> None:
    c = DemoContributor()
    for r in c.get_routes():
        assert r.name


def test_navigation_labels_are_set() -> None:
    c = DemoContributor()
    for n in c.get_navigation_items():
        assert n.label
        assert n.url


def test_contributor_metadata_is_populated() -> None:
    c = DemoContributor()
    assert c.name == "demo"
    assert c.display_name == "Demo Plugin"
    assert c.package_source == "demo"
    assert c.priority == 500
    assert c.version == "0.1.0"
