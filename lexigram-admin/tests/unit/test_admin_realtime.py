"""Tests for admin realtime types."""

import pytest
from datetime import datetime

from lexigram.admin.services.realtime import RealtimeUpdate, UpdateType


class TestUpdateType:
    """Tests for UpdateType enum."""

    def test_update_type_values(self) -> None:
        """Test UpdateType enum values."""
        assert UpdateType.METRIC.value == "metric"
        assert UpdateType.CHART.value == "chart"
        assert UpdateType.TABLE.value == "table"
        assert UpdateType.NOTIFICATION.value == "notification"
        assert UpdateType.CUSTOM.value == "custom"

    def test_update_type_members(self) -> None:
        """Test UpdateType has expected members."""
        members = list(UpdateType)
        assert len(members) == 5


class TestRealtimeUpdate:
    """Tests for RealtimeUpdate dataclass."""

    def test_realtime_update_defaults(self) -> None:
        """Test RealtimeUpdate default values."""
        update = RealtimeUpdate(
            type=UpdateType.METRIC,
            data={"value": 100},
        )
        assert update.type == UpdateType.METRIC
        assert update.data == {"value": 100}
        assert update.target == ""
        assert update.timestamp is not None

    def test_realtime_update_with_target(self) -> None:
        """Test RealtimeUpdate with target."""
        update = RealtimeUpdate(
            type=UpdateType.TABLE,
            data={"rows": []},
            target="users-table",
        )
        assert update.target == "users-table"

    def test_realtime_update_to_json(self) -> None:
        """Test RealtimeUpdate to_json."""
        update = RealtimeUpdate(
            type=UpdateType.METRIC,
            data={"value": 100},
        )
        json_str = update.to_json()
        assert "metric" in json_str
        assert "value" in json_str
