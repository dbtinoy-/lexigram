"""Tests for dashboard widget types."""

import pytest

from lexigram.admin.dashboard.widgets import WidgetConfig, WidgetType


class TestWidgetType:
    """Tests for WidgetType enum."""

    def test_widget_type_values(self) -> None:
        """Test WidgetType enum values."""
        assert WidgetType.METRIC.value == "metric"
        assert WidgetType.CHART.value == "chart"
        assert WidgetType.TABLE.value == "table"
        assert WidgetType.TEXT.value == "text"
        assert WidgetType.CUSTOM.value == "custom"
        assert WidgetType.STAT_CARD.value == "stat_card"
        assert WidgetType.ACTIVITY.value == "activity"
        assert WidgetType.HEALTH.value == "health"

    def test_widget_type_members(self) -> None:
        """Test WidgetType has expected members."""
        members = list(WidgetType)
        assert len(members) == 8


class TestWidgetConfig:
    """Tests for WidgetConfig dataclass."""

    def test_widget_config_required(self) -> None:
        """Test WidgetConfig with required fields."""
        config = WidgetConfig(
            id="widget-1",
            type=WidgetType.METRIC,
            title="My Widget",
        )
        assert config.id == "widget-1"
        assert config.type == WidgetType.METRIC
        assert config.title == "My Widget"

    def test_widget_config_defaults(self) -> None:
        """Test WidgetConfig default values."""
        config = WidgetConfig(
            id="widget-1",
            type=WidgetType.METRIC,
            title="My Widget",
        )
        assert config.config == {}
        assert config.position == {"x": 0, "y": 0, "w": 1, "h": 1}

    def test_widget_config_with_options(self) -> None:
        """Test WidgetConfig with optional fields."""
        config = WidgetConfig(
            id="widget-1",
            type=WidgetType.CHART,
            title="Chart Widget",
            config={"chart_type": "bar"},
            position={"x": 2, "y": 3, "w": 4, "h": 2},
        )
        assert config.config == {"chart_type": "bar"}
        assert config.position == {"x": 2, "y": 3, "w": 4, "h": 2}

    def test_widget_config_to_dict(self) -> None:
        """Test WidgetConfig to_dict."""
        config = WidgetConfig(
            id="widget-1",
            type=WidgetType.METRIC,
            title="My Widget",
        )
        d = config.to_dict()
        assert d["id"] == "widget-1"
        assert d["type"] == "metric"
        assert d["title"] == "My Widget"

    def test_widget_config_from_dict(self) -> None:
        """Test WidgetConfig from_dict."""
        data = {
            "id": "widget-1",
            "type": "chart",
            "title": "Chart Widget",
            "config": {"key": "value"},
            "position": {"x": 1, "y": 2, "w": 3, "h": 4},
        }
        config = WidgetConfig.from_dict(data)
        assert config.id == "widget-1"
        assert config.type == WidgetType.CHART
        assert config.config == {"key": "value"}
