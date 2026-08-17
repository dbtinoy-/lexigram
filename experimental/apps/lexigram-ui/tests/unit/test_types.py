"""Tests for UI types."""

import pytest

from lexigram.ui.types import Breadcrumb, NavItem


class TestNavItem:
    """Tests for NavItem."""

    def test_basic_nav_item(self) -> None:
        """Test basic navigation item creation."""
        item = NavItem(label="Home", url="/")
        assert item.label == "Home"
        assert item.url == "/"
        assert item.icon is None
        assert item.active is False

    def test_nav_item_with_icon(self) -> None:
        """Test navigation item with icon."""
        item = NavItem(label="Home", url="/", icon="home")
        assert item.icon == "home"

    def test_nav_item_active(self) -> None:
        """Test active navigation item."""
        item = NavItem(label="Home", url="/", active=True)
        assert item.active is True

    def test_nav_item_with_children(self) -> None:
        """Test navigation item with children."""
        child = NavItem(label="Sub", url="/sub")
        item = NavItem(label="Parent", url="/parent", children=[child])
        assert len(item.children) == 1
        assert item.children[0].label == "Sub"

    def test_nav_item_children_empty_by_default(self) -> None:
        """Test children list defaults to empty."""
        item = NavItem(label="Home", url="/")
        assert item.children == []

    def test_nav_item_nested_children(self) -> None:
        """Test nested children."""
        grandchild = NavItem(label="Grandchild", url="/grandchild")
        child = NavItem(label="Child", url="/child", children=[grandchild])
        parent = NavItem(label="Parent", url="/parent", children=[child])
        assert len(parent.children) == 1
        assert len(parent.children[0].children) == 1


class TestBreadcrumb:
    """Tests for Breadcrumb."""

    def test_basic_breadcrumb(self) -> None:
        """Test basic breadcrumb creation."""
        crumb = Breadcrumb(label="Home", url="/")
        assert crumb.label == "Home"
        assert crumb.url == "/"
        assert crumb.active is False

    def test_breadcrumb_optional_url(self) -> None:
        """Test breadcrumb with optional URL."""
        crumb = Breadcrumb(label="Current")
        assert crumb.url is None

    def test_breadcrumb_active(self) -> None:
        """Test active breadcrumb."""
        crumb = Breadcrumb(label="Current", active=True)
        assert crumb.active is True

    def test_breadcrumb_inactive_by_default(self) -> None:
        """Test default active is False."""
        crumb = Breadcrumb(label="Home", url="/")
        assert crumb.active is False

    def test_breadcrumb_url_none_by_default(self) -> None:
        """Test URL defaults to None."""
        crumb = Breadcrumb(label="Current")
        assert crumb.url is None


class TestTypesExport:
    """Tests for types module exports."""

    def test_nav_item_exported(self) -> None:
        """Test NavItem is in module exports."""
        from lexigram.ui import types

        assert hasattr(types, "NavItem")

    def test_breadcrumb_exported(self) -> None:
        """Test Breadcrumb is in module exports."""
        from lexigram.ui import types

        assert hasattr(types, "Breadcrumb")