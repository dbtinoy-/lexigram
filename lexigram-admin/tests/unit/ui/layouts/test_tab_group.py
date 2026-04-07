from __future__ import annotations

from lexigram.admin.schema import TextField
from lexigram.admin.ui.layouts.tab_group import Tab, TabGroup
from lexigram.ui import Element


class TestTab:
    def test_construct_with_minimum_args(self) -> None:
        tab = Tab(name="general", label="General")
        assert tab.name == "general"
        assert tab.label == "General"

    def test_construct_with_all_args(self) -> None:
        tab = Tab(
            name="settings",
            label="Settings",
            schema_fields=[TextField(name="key")],
            icon="<svg></svg>",
            badge=3,
        )
        assert tab.name == "settings"
        assert len(tab.schema_fields) == 1


class TestTabGroup:
    def test_construct_with_tabs(self) -> None:
        tabs = [
            Tab(name="general", label="General"),
            Tab(name="settings", label="Settings"),
        ]
        group = TabGroup(tabs=tabs)
        assert len(group.tabs) == 2

    def test_render_returns_element(self) -> None:
        tabs = [Tab(name="general", label="General")]
        group = TabGroup(tabs=tabs)
        element = group.render()
        assert isinstance(element, Element)

    def test_render_empty_tabs(self) -> None:
        group = TabGroup(tabs=[])
        element = group.render()
        output = str(element)
        assert "<div" in output

    def test_render_shows_tab_labels(self) -> None:
        tabs = [
            Tab(name="general", label="General"),
            Tab(name="settings", label="Settings"),
        ]
        group = TabGroup(tabs=tabs)
        output = str(group.render())
        assert "General" in output
        assert "Settings" in output

    def test_render_tab_role_attributes(self) -> None:
        tabs = [Tab(name="general", label="General")]
        group = TabGroup(tabs=tabs)
        output = str(group.render())
        assert 'role="tab"' in output
        assert 'role="tablist"' in output
        assert 'role="tabpanel"' in output

    def test_render_with_badge(self) -> None:
        tabs = [Tab(name="general", label="General", badge=5)]
        group = TabGroup(tabs=tabs)
        output = str(group.render())
        assert "5" in output

    def test_render_with_icon(self) -> None:
        tabs = [Tab(name="general", label="General", icon="<svg></svg>")]
        group = TabGroup(tabs=tabs)
        output = str(group.render())
        assert "<svg" in output

    def test_render_with_schema_fields(self) -> None:
        tabs = [
            Tab(
                name="general",
                label="General",
                schema_fields=[TextField(name="title")],
            ),
        ]
        group = TabGroup(tabs=tabs)
        output = str(group.render())
        assert "title" in output

    def test_default_tab(self) -> None:
        tabs = [
            Tab(name="general", label="General"),
            Tab(name="settings", label="Settings"),
        ]
        group = TabGroup(tabs=tabs, default_tab="settings")
        output = str(group.render())
        assert "settings" in output
