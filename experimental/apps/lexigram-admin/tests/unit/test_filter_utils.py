"""Tests for filter badges, state detection, defaults, and conversion utilities."""

from __future__ import annotations

import pytest

from lexigram.admin.services.filter_manager import (
    FilterDefinition,
    FilterManager,
    FilterPreset,
)


@pytest.fixture
def filter_definitions():
    """Create sample filter definitions."""
    from lexigram.admin.ui.filters.types import RangeFilter, SelectFilter, ToggleFilter

    return [
        FilterDefinition(
            "status",
            filter=SelectFilter(options=["active", "inactive"]),
            label="Status",
        ),
        FilterDefinition(
            "category",
            filter=SelectFilter(options=["tech", "business", "personal"]),
            label="Category",
        ),
        FilterDefinition(
            "price",
            filter=None,
            label="Price",
            validator=lambda x: float(x) >= 0,
        ),
        FilterDefinition("created_at", filter=RangeFilter(), label="Created Date"),
        FilterDefinition("is_featured", filter=ToggleFilter(), label="Featured"),
        FilterDefinition("tags", filter=None, label="Tags", default_value=""),
    ]


@pytest.fixture
def filter_manager(filter_definitions):
    """Create filter manager with definitions."""
    return FilterManager(filter_definitions)


def test_get_active_filter_badges(filter_manager):
    filters = {
        "status": "active",
        "price": "100",
        "category": "tech",
    }
    badges = filter_manager.get_active_filter_badges(filters)
    assert len(badges) == 3
    assert any(b["field"] == "status" and b["value"] == "active" for b in badges)
    assert any(b["label"] == "Price" for b in badges)


def test_get_active_filter_badges_skips_empty(filter_manager):
    filters = {
        "status": "active",
        "price": "",
        "category": None,
    }
    badges = filter_manager.get_active_filter_badges(filters)
    assert len(badges) == 1
    assert badges[0]["field"] == "status"


def test_get_active_filter_badges_complex_values(filter_manager):
    filters = {
        "tags": ["python", "async"],
    }
    badges = filter_manager.get_active_filter_badges(filters)
    assert len(badges) == 1
    assert "python, async" in badges[0]["value"]


def test_clear_all_filters(filter_manager):
    cleared = filter_manager.clear_all_filters()
    assert cleared["tags"] == ""


def test_has_active_filters_true(filter_manager):
    filters = {"status": "active"}
    assert filter_manager.has_active_filters(filters) is True


def test_has_active_filters_false(filter_manager):
    filters = {}
    assert filter_manager.has_active_filters(filters) is False


def test_has_active_filters_only_defaults(filter_manager):
    filters = {"tags": ""}
    assert filter_manager.has_active_filters(filters) is False


def test_filter_definition_defaults():
    definition = FilterDefinition("test_field")
    assert definition.field == "test_field"
    assert definition.filter is None
    assert definition.label is None
    assert definition.required is False


def test_filter_preset_defaults():
    preset = FilterPreset(name="Test", filters={"key": "value"})
    assert preset.name == "Test"
    assert preset.user_id is None
    assert preset.is_default is False
    assert preset.is_shared is False


def test_to_filter_set_scalar_becomes_eq(filter_manager):
    fs = filter_manager.to_filter_set({"status": "active"})
    assert len(fs["conditions"]) == 1
    assert fs["conditions"][0]["field"] == "status"
    assert fs["conditions"][0]["operator"] == "eq"
    assert fs["conditions"][0]["value"] == "active"


def test_to_filter_set_list_becomes_in(filter_manager):
    fs = filter_manager.to_filter_set({"tags": ["python", "async"]})
    assert len(fs["conditions"]) == 1
    assert fs["conditions"][0]["operator"] == "in"
    assert fs["conditions"][0]["value"] == ["python", "async"]


def test_to_filter_set_none_becomes_is_null(filter_manager):
    fs = filter_manager.to_filter_set({"deleted_at": None})
    assert len(fs["conditions"]) == 1
    assert fs["conditions"][0]["operator"] == "is_null"


def test_to_filter_set_empty_string_skipped(filter_manager):
    fs = filter_manager.to_filter_set({"status": "active", "price": ""})
    assert len(fs["conditions"]) == 1
    assert fs["conditions"][0]["field"] == "status"


def test_to_filter_set_pagination_forwarded(filter_manager):
    fs = filter_manager.to_filter_set(
        {"status": "active"},
        order_by="created_at",
        order_dir="desc",
        page=3,
        page_size=50,
    )
    assert fs["order_by"] == "created_at"
    assert fs["order_dir"] == "desc"
    assert fs["page"] == 3
    assert fs["page_size"] == 50


def test_to_filter_set_search_query_forwarded(filter_manager):
    fs = filter_manager.to_filter_set({"status": "active"}, search_query="hello")
    assert fs["search_query"] == "hello"


def test_to_search_query_returns_search_query(filter_manager):
    with pytest.raises(RuntimeError):
        filter_manager.to_search_query({"status": "active"}, search_query="test")


def test_to_search_query_custom_translator(filter_definitions):
    from unittest.mock import MagicMock

    mock_translator = MagicMock()
    mock_translator.translate.return_value = {"q": "mocked"}

    fm = FilterManager(filter_definitions, translator=mock_translator)
    sq = fm.to_search_query({"status": "active"})

    mock_translator.translate.assert_called_once()
    assert sq["q"] == "mocked"
