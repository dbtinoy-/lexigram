"""Tests for header manager types."""

import pytest

from lexigram.admin.actions.header_manager.types import (
    ColumnVisibilityConfig,
    DensityConfig,
    HeaderAction,
    HeaderActionStyle,
    TableDensity,
)


class TestHeaderActionStyle:
    """Tests for HeaderActionStyle enum."""

    def test_header_action_style_values(self) -> None:
        """Test HeaderActionStyle enum values."""
        assert HeaderActionStyle.PRIMARY.value == "primary"
        assert HeaderActionStyle.SECONDARY.value == "secondary"
        assert HeaderActionStyle.SUCCESS.value == "success"
        assert HeaderActionStyle.DANGER.value == "danger"
        assert HeaderActionStyle.WARNING.value == "warning"
        assert HeaderActionStyle.INFO.value == "info"

    def test_header_action_style_members(self) -> None:
        """Test HeaderActionStyle has expected members."""
        members = list(HeaderActionStyle)
        assert len(members) == 6


class TestTableDensity:
    """Tests for TableDensity enum."""

    def test_table_density_values(self) -> None:
        """Test TableDensity enum values."""
        assert TableDensity.COMPACT.value == "compact"
        assert TableDensity.NORMAL.value == "normal"
        assert TableDensity.COMFORTABLE.value == "comfortable"

    def test_table_density_members(self) -> None:
        """Test TableDensity has expected members."""
        members = list(TableDensity)
        assert len(members) == 3


class TestHeaderAction:
    """Tests for HeaderAction dataclass."""

    def test_header_action_defaults(self) -> None:
        """Test HeaderAction default values."""
        action = HeaderAction(name="test", label="Test Action")
        assert action.name == "test"
        assert action.label == "Test Action"
        assert action.handler is None
        assert action.icon is None
        assert action.style == HeaderActionStyle.SECONDARY
        assert action.url is None
        assert action.method == "GET"
        assert action.open_in_modal is False

    def test_header_action_with_options(self) -> None:
        """Test HeaderAction with options."""
        action = HeaderAction(
            name="test",
            label="Test",
            icon="plus",
            style=HeaderActionStyle.SUCCESS,
            url="/test",
            method="POST",
            open_in_modal=True,
            tooltip="Test tooltip",
        )
        assert action.icon == "plus"
        assert action.style == HeaderActionStyle.SUCCESS
        assert action.url == "/test"
        assert action.method == "POST"
        assert action.open_in_modal is True
        assert action.tooltip == "Test tooltip"


class TestColumnVisibilityConfig:
    """Tests for ColumnVisibilityConfig dataclass."""

    def test_column_visibility_defaults(self) -> None:
        """Test ColumnVisibilityConfig default values."""
        config = ColumnVisibilityConfig()
        assert config.enabled is True
        assert config.default_visible == []
        assert config.always_visible == []
        assert config.save_preference is True
        assert config.storage_key == "table_column_visibility"

    def test_column_visibility_with_columns(self) -> None:
        """Test ColumnVisibilityConfig with columns."""
        config = ColumnVisibilityConfig(
            default_visible=["col1", "col2"],
            always_visible=["id"],
        )
        assert config.default_visible == ["col1", "col2"]
        assert config.always_visible == ["id"]


class TestDensityConfig:
    """Tests for DensityConfig dataclass."""

    def test_density_config_defaults(self) -> None:
        """Test DensityConfig default values."""
        config = DensityConfig()
        assert config.enabled is True
        assert config.default == TableDensity.NORMAL
        assert len(config.options) == 3
        assert config.save_preference is True

    def test_density_config_with_options(self) -> None:
        """Test DensityConfig with custom options."""
        config = DensityConfig(
            default=TableDensity.COMPACT,
            options=[TableDensity.COMPACT],
        )
        assert config.default == TableDensity.COMPACT
        assert len(config.options) == 1
