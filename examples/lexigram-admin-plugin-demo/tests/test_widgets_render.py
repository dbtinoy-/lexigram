from __future__ import annotations

from demo.widgets.widget_count import (
    make_widget_definitions,
    make_widget_routes,
    widget_count_handler,
)


async def test_widget_count_handler_returns_html() -> None:
    result = await widget_count_handler(request=None)
    assert isinstance(result, str)
    assert "widgets" in result
    assert "42" in result


async def test_widget_count_handler_contains_expected_html() -> None:
    result = await widget_count_handler(request=None)
    assert "<strong>42</strong>" in result


def test_widget_definitions_are_returned() -> None:
    definitions = make_widget_definitions()
    assert len(definitions) >= 1


def test_widget_definition_has_correct_attributes() -> None:
    definitions = make_widget_definitions()
    widget = definitions[0]
    assert widget.name == "widget_count"
    assert widget.title == "Widget Count"
    assert widget.contributor == "demo"
    assert widget.render_endpoint == "/admin/demo/widgets/count"
    assert widget.description == "Total widget count"


def test_widget_routes_are_returned() -> None:
    routes = make_widget_routes()
    assert len(routes) >= 1


def test_widget_route_has_correct_attributes() -> None:
    routes = make_widget_routes()
    route = routes[0]
    assert route.path == "/admin/demo/widgets/count"
    assert route.method == "GET"
    assert route.name == "widgets.count"
