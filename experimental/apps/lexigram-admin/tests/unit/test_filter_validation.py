"""Tests for filter validation and URL encoding/decoding."""

from __future__ import annotations

import pytest

from lexigram.admin.services.filter_manager import FilterManager


@pytest.fixture
def filter_definitions():
    """Create sample filter definitions."""
    from lexigram.admin.ui.filters.types import RangeFilter, SelectFilter, ToggleFilter

    from lexigram.admin.services.filter_manager import FilterDefinition

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


@pytest.mark.asyncio
async def test_validate_filters_valid(filter_manager):
    filters = {
        "status": "active",
        "price": "100.50",
        "category": "tech",
    }
    is_valid, errors = await filter_manager.validate_filters(filters)
    assert is_valid
    assert errors == {}


@pytest.mark.asyncio
async def test_validate_filters_invalid_option(filter_manager):
    filters = {"status": "unknown"}
    is_valid, errors = await filter_manager.validate_filters(filters)
    assert not is_valid
    assert "status" in errors


@pytest.mark.asyncio
async def test_validate_filters_invalid_number(filter_manager):
    filters = {"price": "not_a_number"}
    is_valid, errors = await filter_manager.validate_filters(filters)
    assert not is_valid
    assert "price" in errors


@pytest.mark.asyncio
async def test_validate_filters_custom_validator(filter_manager):
    filters = {"price": "-10"}
    is_valid, errors = await filter_manager.validate_filters(filters)
    assert not is_valid
    assert "price" in errors


@pytest.mark.asyncio
async def test_validate_filters_unknown_field(filter_manager):
    filters = {"unknown_field": "value"}
    is_valid, errors = await filter_manager.validate_filters(filters)
    assert not is_valid
    assert "unknown_field" in errors


def test_encode_to_url(filter_manager):
    filters = {
        "status": "active",
        "price": "100",
        "category": "tech",
    }
    url = filter_manager.encode_to_url(filters)
    assert "filter%5Bstatus%5D=active" in url or "filter[status]=active" in url
    assert "price" in url
    assert "category" in url


def test_encode_to_url_complex_values(filter_manager):
    filters = {
        "tags": ["python", "async"],
        "meta": {"key": "value"},
    }
    url = filter_manager.encode_to_url(filters)
    assert "tags" in url
    assert "meta" in url


def test_encode_to_url_skips_empty(filter_manager):
    filters = {
        "status": "active",
        "price": "",
        "category": None,
    }
    url = filter_manager.encode_to_url(filters)
    assert "status" in url
    assert "price" not in url
    assert "category" not in url


def test_decode_from_url(filter_manager):
    query_string = "filter[status]=active&filter[price]=100"
    filters = filter_manager.decode_from_url(query_string)
    assert filters["status"] == "active"
    assert filters["price"] == 100


def test_decode_from_url_with_question_mark(filter_manager):
    query_string = "?filter[status]=active&filter[price]=100"
    filters = filter_manager.decode_from_url(query_string)
    assert filters["status"] == "active"
    assert filters["price"] == 100


def test_decode_from_url_complex_values(filter_manager):
    from lexigram.serialization import dumps_str

    tags = dumps_str(["python", "async"])
    query_string = f"filter[tags]={tags}"
    filters = filter_manager.decode_from_url(query_string)
    assert filters["tags"] == ["python", "async"]


def test_get_default_filters(filter_manager):
    defaults = filter_manager.get_default_filters()
    assert defaults["tags"] == ""
    assert "status" not in defaults


def test_round_trip_url_encoding(filter_manager):
    original_filters = {
        "status": "active",
        "price": 100,
        "category": "tech",
    }
    url = filter_manager.encode_to_url(original_filters)
    decoded_filters = filter_manager.decode_from_url(url)
    assert decoded_filters == original_filters
