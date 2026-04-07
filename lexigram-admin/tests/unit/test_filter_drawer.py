"""Tests for stacked/sidebar FilterDrawer component."""

from __future__ import annotations

import pytest

from lexigram.admin.ui.organisms.filter_drawer import FilterDrawer


class TestFilterDrawerRender:
    def test_render_returns_component(self) -> None:
        drawer = FilterDrawer()
        result = drawer.render()
        assert result is not None

    def test_render_contains_alpine_data(self) -> None:
        drawer = FilterDrawer()
        html = str(drawer.render())
        assert "filterDrawerOpen" in html

    def test_trigger_button_renders(self) -> None:
        drawer = FilterDrawer()
        html = str(drawer.render())
        assert "Filters" in html

    def test_backdrop_renders(self) -> None:
        drawer = FilterDrawer()
        html = str(drawer.render())
        # backdrop uses x-show to toggle visibility
        assert "filterDrawerOpen" in html

    def test_panel_renders_apply_button(self) -> None:
        drawer = FilterDrawer(resource_prefix="/admin/users")
        html = str(drawer.render())
        assert "Apply filters" in html

    def test_panel_renders_reset_link(self) -> None:
        drawer = FilterDrawer(resource_prefix="/admin/users")
        html = str(drawer.render())
        assert "Reset all" in html


class TestFilterDrawerActiveBadge:
    def test_no_badge_when_no_active_filters(self) -> None:
        drawer = FilterDrawer(current_values={})
        active = drawer._active_filter_count()
        assert active == 0

    def test_counts_non_empty_values(self) -> None:
        drawer = FilterDrawer(
            current_values={"role": "admin", "is_active": "true", "search": ""}
        )
        active = drawer._active_filter_count()
        assert active == 2

    def test_ignores_none_values(self) -> None:
        drawer = FilterDrawer(
            current_values={"role": None, "status": "active"}
        )
        active = drawer._active_filter_count()
        assert active == 1

    def test_ignores_empty_list_values(self) -> None:
        drawer = FilterDrawer(current_values={"tags": [], "role": "admin"})
        active = drawer._active_filter_count()
        assert active == 1

    def test_badge_in_html_when_active(self) -> None:
        drawer = FilterDrawer(
            current_values={"role": "admin"},
        )
        html = str(drawer.render())
        # Badge shows count "1"
        assert ">1<" in html or "1</span>" in html


class TestFilterDrawerWithDictFilters:
    def test_dict_filters_render_inputs(self) -> None:
        drawer = FilterDrawer(
            filters={"status": {"type": "select", "options": ["active", "inactive"]}},
            current_values={"status": "active"},
        )
        html = str(drawer.render())
        assert "status" in html.lower()

    def test_dict_filter_label_displayed(self) -> None:
        drawer = FilterDrawer(
            filters={"user_role": {}},
        )
        html = str(drawer.render())
        assert "User Role" in html


class TestFilterDrawerWithObjectFilters:
    """Test FilterDrawer with filter objects that have .render()."""

    def _make_mock_filter(self, field_name: str, label: str) -> object:
        class MockFilter:
            def __init__(self) -> None:
                self.field_name = field_name
                self.label = label

            def set_state(self, state: object) -> None:
                pass

            def render(self, value: object = None, url: str | None = None) -> str:
                return f'<input name="{self.field_name}" value="{value or ""}">'

        return MockFilter()

    def test_object_filters_render(self) -> None:
        f = self._make_mock_filter("status", "Status")
        drawer = FilterDrawer(filters=[f], current_values={"status": "active"})
        html = str(drawer.render())
        assert "status" in html

    def test_empty_filter_list_renders_panel(self) -> None:
        drawer = FilterDrawer(filters=[])
        result = drawer.render()
        assert result is not None


class TestFilterDrawerHTMXAttrs:
    def test_apply_button_has_hx_get(self) -> None:
        drawer = FilterDrawer(resource_prefix="/admin/users")
        html = str(drawer.render())
        assert "hx-get" in html

    def test_apply_targets_data_zone(self) -> None:
        drawer = FilterDrawer(resource_prefix="/admin/users")
        html = str(drawer.render())
        assert 'hx-target="#table-data"' in html

    def test_apply_targets_data_zone_swap(self) -> None:
        drawer = FilterDrawer(resource_prefix="/admin/users")
        html = str(drawer.render())
        assert 'hx-swap="innerHTML"' in html
