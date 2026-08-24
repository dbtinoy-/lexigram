from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.controllers.dashboard import DashboardController


class TestGetResourceList:
    @pytest.fixture
    def controller(self) -> DashboardController:
        return DashboardController(renderer=MagicMock(), assembler=None)

    @pytest.fixture
    def mock_request(self) -> MagicMock:
        request = MagicMock()
        request.app.state.admin_resources = {
            "z_resource": ...,
            "a_resource": ...,
        }
        return request

    def test_returns_sorted_names(
        self,
        controller: DashboardController,
        mock_request: MagicMock,
    ) -> None:
        names = controller._get_resource_list(mock_request)
        assert names == ["a_resource", "z_resource"]

    def test_returns_empty_when_no_state(
        self,
        controller: DashboardController,
        mock_request: MagicMock,
    ) -> None:
        mock_request.app = MagicMock(spec_set=())
        result = controller._get_resource_list(mock_request)
        assert result == []

    def test_returns_empty_when_no_admin_resources(
        self,
        controller: DashboardController,
        mock_request: MagicMock,
    ) -> None:
        mock_request.app.state.admin_resources = {}
        result = controller._get_resource_list(mock_request)
        assert result == []


class TestTimeSeriesHelpers:
    @pytest.fixture
    def controller(self) -> DashboardController:
        return DashboardController(renderer=MagicMock(), assembler=None)

    def test_format_time_series_basic(
        self,
        controller: DashboardController,
    ) -> None:
        data = [(datetime(2024, 1, 15, 10, 30), 42.0)]
        result = controller.format_time_series(data, interval="hour")
        assert len(result) == 1
        entry = result[0]
        assert "timestamp" in entry
        assert entry["value"] == 42.0
        assert entry["label"] == "10:30"

    def test_format_time_series_different_intervals(
        self,
        controller: DashboardController,
    ) -> None:
        ts = datetime(2024, 6, 15, 14, 30)
        data = [(ts, 10.0)]

        hour_result = controller.format_time_series(data, interval="hour")
        day_result = controller.format_time_series(data, interval="day")
        week_result = controller.format_time_series(data, interval="week")
        month_result = controller.format_time_series(data, interval="month")

        assert hour_result[0]["label"] == "14:30"
        assert day_result[0]["label"] == "2024-06-15"
        assert week_result[0]["label"] == "Week 24, 2024"
        assert month_result[0]["label"] == "Jun 2024"

    def test_aggregate_time_series_buckets(
        self,
        controller: DashboardController,
    ) -> None:
        ts = datetime(2024, 1, 15, 10, 15)
        data = [
            (ts, 10.0),
            (ts.replace(minute=30), 20.0),
            (ts.replace(minute=45), 30.0),
        ]
        result = controller.aggregate_time_series(data, interval="hour")
        assert len(result) == 1
        _, avg = result[0]
        assert avg == 20.0

    def test_get_bucket_key_roundtrip(
        self,
        controller: DashboardController,
    ) -> None:
        ts = datetime(2024, 3, 15, 8, 30)
        for interval in ("hour", "day", "week", "month"):
            key = controller._get_bucket_key(ts, interval)
            parsed = controller._parse_bucket_key(key, interval)
            assert parsed.year == ts.year
            assert parsed.month == ts.month


class TestRequestCache:
    @pytest.fixture
    def controller(self) -> DashboardController:
        return DashboardController(renderer=MagicMock(), assembler=None)

    def test_get_request_cache_returns_dict(
        self,
        controller: DashboardController,
    ) -> None:
        mock_request = MagicMock()
        cache = controller.get_request_cache(mock_request)
        assert isinstance(cache, dict)

    @pytest.mark.asyncio
    async def test_aggregate_metric_uses_cache(
        self,
        controller: DashboardController,
    ) -> None:
        mock_request = MagicMock()
        shared_cache: dict[str, object] = {}
        controller.get_request_cache = MagicMock(  # type: ignore[method-assign]
            return_value=shared_cache,
        )

        compute = AsyncMock(return_value=42)

        result1 = await controller.aggregate_metric(
            mock_request,
            "test_metric",
            compute,
            use_request_cache=True,
        )
        result2 = await controller.aggregate_metric(
            mock_request,
            "test_metric",
            compute,
            use_request_cache=True,
        )

        assert result1 == 42
        assert result2 == 42
        compute.assert_called_once()
