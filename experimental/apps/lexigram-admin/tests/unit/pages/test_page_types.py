"""Tests for page types (PageResponse, NavigationEntry)."""

from __future__ import annotations

from lexigram.admin.pages.types import NavigationEntry, PageResponse


class TestPageResponse:
    """Tests for PageResponse dataclass."""

    def test_can_be_constructed_with_content_and_title(self) -> None:
        response = PageResponse(content="<h1>Hello</h1>", title="Dashboard")
        assert response.content == "<h1>Hello</h1>"
        assert response.title == "Dashboard"

    def test_breadcrumbs_default_to_none(self) -> None:
        response = PageResponse(content="<h1>Hello</h1>", title="Dashboard")
        assert response.breadcrumbs is None

    def test_has_breadcrumbs_false_when_none(self) -> None:
        response = PageResponse(content="<h1>Hello</h1>", title="Dashboard")
        assert response.has_breadcrumbs is False

    def test_has_breadcrumbs_false_when_empty_list(self) -> None:
        response = PageResponse(
            content="<h1>Hello</h1>",
            title="Dashboard",
            breadcrumbs=[],
        )
        assert response.has_breadcrumbs is False

    def test_has_breadcrumbs_true_when_has_items(self) -> None:
        response = PageResponse(
            content="<h1>Hello</h1>",
            title="Dashboard",
            breadcrumbs=[("Home", "/"), ("Dashboard", "/dashboard")],
        )
        assert response.has_breadcrumbs is True


class TestNavigationEntry:
    """Tests for NavigationEntry dataclass."""

    def test_can_be_constructed_with_label_and_url(self) -> None:
        entry = NavigationEntry(label="Dashboard", url="/admin/dashboard")
        assert entry.label == "Dashboard"
        assert entry.url == "/admin/dashboard"

    def test_icon_defaults_to_none(self) -> None:
        entry = NavigationEntry(label="Dashboard", url="/admin/dashboard")
        assert entry.icon is None

    def test_permissions_defaults_to_none(self) -> None:
        entry = NavigationEntry(label="Dashboard", url="/admin/dashboard")
        assert entry.permissions is None

    def test_active_defaults_to_false(self) -> None:
        entry = NavigationEntry(label="Dashboard", url="/admin/dashboard")
        assert entry.active is False
