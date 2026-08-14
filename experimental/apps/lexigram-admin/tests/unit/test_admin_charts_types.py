"""Tests for admin chart service types."""

import pytest

from lexigram.admin.services.charts import (
    ChartBackend,
    ChartData,
    ChartType,
)


class TestChartBackend:
    """Tests for ChartBackend enum."""

    def test_chart_backend_values(self) -> None:
        """Test ChartBackend enum values."""
        assert ChartBackend.CHARTJS.value == "chartjs"
        assert ChartBackend.PLOTLY.value == "plotly"

    def test_chart_backend_members(self) -> None:
        """Test ChartBackend has expected members."""
        members = list(ChartBackend)
        assert len(members) == 2


class TestChartType:
    """Tests for ChartType enum."""

    def test_chart_type_values(self) -> None:
        """Test ChartType enum values."""
        assert ChartType.LINE.value == "line"
        assert ChartType.BAR.value == "bar"
        assert ChartType.PIE.value == "pie"
        assert ChartType.SCATTER.value == "scatter"
        assert ChartType.AREA.value == "area"
        assert ChartType.DONUT.value == "donut"

    def test_chart_type_members(self) -> None:
        """Test ChartType has expected members."""
        members = list(ChartType)
        assert len(members) == 6

    def test_chart_type_from_string(self) -> None:
        """Test creating ChartType from string."""
        assert ChartType("line") == ChartType.LINE
        assert ChartType("pie") == ChartType.PIE


class TestChartData:
    """Tests for ChartData dataclass."""

    def test_chart_data_defaults(self) -> None:
        """Test ChartData default values."""
        data = ChartData()
        assert data.labels == []
        assert data.datasets == []
        assert data.title == ""
        assert data.x_label == ""
        assert data.y_label == ""

    def test_chart_data_with_values(self) -> None:
        """Test ChartData with values."""
        data = ChartData(
            labels=["Jan", "Feb", "Mar"],
            datasets=[{"data": [10, 20, 30], "label": "Sales"}],
            title="Monthly Sales",
            x_label="Month",
            y_label="Revenue",
        )
        assert data.labels == ["Jan", "Feb", "Mar"]
        assert len(data.datasets) == 1
        assert data.title == "Monthly Sales"
        assert data.x_label == "Month"
        assert data.y_label == "Revenue"
