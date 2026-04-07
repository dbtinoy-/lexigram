"""Tests for UI atoms/icons."""

import pytest

from lexigram.ui.atoms import icons


class TestIcons:
    """Tests for icon system."""

    def test_icons_dict_exists(self) -> None:
        """Test ICONS dict exists."""
        assert hasattr(icons, "ICONS")
        assert isinstance(icons.ICONS, dict)

    def test_home_icon_exists(self) -> None:
        """Test home icon is defined."""
        assert "home" in icons.ICONS

    def test_navigation_icons(self) -> None:
        """Test navigation icons are defined."""
        assert "menu" in icons.ICONS
        assert "chevron-left" in icons.ICONS
        assert "chevron-right" in icons.ICONS

    def test_user_icons(self) -> None:
        """Test user management icons."""
        assert "user-plus" in icons.ICONS
        assert "user-minus" in icons.ICONS
        assert "user-check" in icons.ICONS
        assert "users" in icons.ICONS

    def test_action_icons(self) -> None:
        """Test action icons."""
        assert "plus" in icons.ICONS
        assert "pencil" in icons.ICONS
        assert "trash" in icons.ICONS
        assert "eye" in icons.ICONS
        assert "search" in icons.ICONS

    def test_file_icons(self) -> None:
        """Test file/document icons."""
        assert "file-text" in icons.ICONS
        assert "image" in icons.ICONS

    def test_status_icons(self) -> None:
        """Test status icons."""
        assert "check" in icons.ICONS
        assert "alert-circle" in icons.ICONS
        assert "info" in icons.ICONS
        assert "x" in icons.ICONS

    def test_chart_icons(self) -> None:
        """Test chart/graph icons."""
        assert "chart-bar" in icons.ICONS
        assert "trending-up" in icons.ICONS
        assert "trending-down" in icons.ICONS

    def test_layout_icons(self) -> None:
        """Test layout icons."""
        assert "grid" in icons.ICONS
        assert "list" in icons.ICONS
        assert "layout" in icons.ICONS


class TestGetIcon:
    """Tests for get_icon function."""

    def test_get_icon_returns_result(self) -> None:
        """Test get_icon returns a result."""
        result = icons.get_icon("home")
        assert result is not None

    def test_get_icon_unknown_returns_empty(self) -> None:
        """Test unknown icon returns fallback."""
        result = icons.get_icon("unknown-icon-xyz")
        assert result is not None

    def test_get_icon_with_custom_class(self) -> None:
        """Test icon with custom class."""
        result = icons.get_icon("home", class_name="text-blue-500")
        assert "text-blue-500" in str(result)

    def test_get_icon_with_size(self) -> None:
        """Test icon with custom size."""
        result = icons.get_icon("home", size="w-6 h-6")
        assert "w-6 h-6" in str(result)

    def test_get_icon_non_string_returns_input(self) -> None:
        """Test non-string input returns appropriate fallback."""
        custom_svg = 123
        result = icons.get_icon(custom_svg)
        assert result == custom_svg

    def test_get_icon_short_emoji(self) -> None:
        """Test short emoji string renders as span."""
        result = icons.get_icon("★")
        assert "span" in str(result)

    def test_get_icon_emits_svg_for_valid_icon(self) -> None:
        """Test valid icon returns SVG element."""
        result = icons.get_icon("check")
        result_str = str(result)
        assert "svg" in result_str

    def test_get_icon_with_additional_attrs(self) -> None:
        """Test additional attributes are passed through."""
        result = icons.get_icon("home", data_testid="home-icon")
        assert "data-testid" in str(result)

    def test_get_icon_empty_string(self) -> None:
        """Test empty string returns fallback."""
        result = icons.get_icon("")
        assert result is not None


class TestIconsContent:
    """Tests for icon SVG content."""

    def test_icon_contains_path_data(self) -> None:
        """Test icons contain path data."""
        home_icon = icons.ICONS["home"]
        assert "path" in home_icon or "M" in home_icon

    def test_menu_icon_svg_paths(self) -> None:
        """Test menu icon has expected structure."""
        menu = icons.ICONS["menu"]
        assert "line" in menu or "M" in menu


class TestIconsDict:
    """Tests for ICONS dictionary properties."""

    def test_icons_not_empty(self) -> None:
        """Test ICONS is not empty."""
        assert len(icons.ICONS) > 0

    def test_icons_all_strings(self) -> None:
        """Test all icon values are strings."""
        for name, content in icons.ICONS.items():
            assert isinstance(content, str), f"Icon {name} is not a string"

    def test_icons_keys_are_strings(self) -> None:
        """Test all icon keys are strings."""
        for name in icons.ICONS.keys():
            assert isinstance(name, str), f"Icon key {name} is not a string"