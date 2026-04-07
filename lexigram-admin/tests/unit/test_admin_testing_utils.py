from unittest.mock import MagicMock

import pytest

from lexigram.admin.resources.base import Resource
from lexigram.admin.ui.actions import Action, BulkAction
from lexigram.admin.ui.columns import BadgeColumn, DateColumn, TextColumn
from lexigram.admin.ui.filters import SelectFilter


class TableTester:
    """Test helper for asserting Resource table configuration."""

    def __init__(self, resource_cls: type[Resource]) -> None:
        self._config = resource_cls.get_table_config()

    def _column_names(self) -> list[str]:
        return [c.name for c in self._config.columns]

    def assert_columns(self, names: list[str], *, strict: bool = False) -> None:
        col_names = self._column_names()
        if strict:
            if set(col_names) != set(names):
                raise AssertionError(
                    f"Strict mismatch: expected {sorted(names)}, got {sorted(col_names)}"
                )
        else:
            missing = [n for n in names if n not in col_names]
            if missing:
                raise AssertionError(f"Missing columns: {missing}")

    def assert_actions(self, names: list[str]) -> None:
        action_names = [a.name for a in self._config.actions]
        missing = [n for n in names if n not in action_names]
        if missing:
            raise AssertionError(f"Missing actions: {missing}")

    def assert_bulk_actions(self, names: list[str]) -> None:
        bulk_names = [a.name for a in self._config.bulk_actions]
        missing = [n for n in names if n not in bulk_names]
        if missing:
            raise AssertionError(f"Missing bulk actions: {missing}")

    def assert_filter_exists(self, name: str) -> None:
        filter_names = [f.name for f in self._config.filters]
        if name not in filter_names:
            raise AssertionError(f"Filter '{name}' not found; available: {filter_names}")


class MockDataGenerator:
    """Generate mock row data for a Resource based on its column config."""

    def __init__(self, resource_cls: type[Resource]) -> None:
        self._config = resource_cls.get_table_config()

    def generate(self, count: int = 5) -> list[dict]:
        col_names = [c.name for c in self._config.columns]
        return [{"id": i + 1, **{name: f"{name}_{i}" for name in col_names}} for i in range(count)]



class SampleResource(Resource):
    def get_table_config():
        config = MagicMock()
        config.columns = [
            TextColumn("name"),
            DateColumn("created_at"),
            BadgeColumn("status"),
        ]
        config.actions = [Action("edit"), Action("delete")]
        config.bulk_actions = [BulkAction("delete")]
        config.filters = [SelectFilter("status", options={})]
        return config


def test_table_tester_assertions():
    tester = TableTester(SampleResource)

    # Passing assertions
    tester.assert_columns(["name", "status"])
    tester.assert_columns(["name", "created_at", "status"], strict=True)
    tester.assert_actions(["edit"])
    tester.assert_bulk_actions(["delete"])
    tester.assert_filter_exists("status")

    # Failing assertions
    with pytest.raises(AssertionError, match="Missing columns"):
        tester.assert_columns(["missing_col"])

    with pytest.raises(AssertionError, match="Strict mismatch"):
        tester.assert_columns(["name"], strict=True)


def test_mock_data_generator():
    generator = MockDataGenerator(SampleResource)
    data = generator.generate(count=5)

    assert len(data) == 5
    first = data[0]

    assert "name" in first
    assert "created_at" in first
    assert "status" in first
    assert "id" in first
    assert first["id"] == 1  # 1-indexed by default logic
