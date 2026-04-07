"""Tests for advanced filter management."""

from __future__ import annotations

import pytest

from lexigram.admin.services.filter_manager import (
    FilterDefinition,
    FilterManager,
    FilterPreset,
)


@pytest.fixture
def filter_definitions():
    """Create sample filter definitions (use concrete filter instances)."""
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
        # Price uses a validator for numeric values
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
    """Test validating valid filters."""
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
    """Test validation fails for invalid option."""
    filters = {"status": "unknown"}

    is_valid, errors = await filter_manager.validate_filters(filters)

    assert not is_valid
    assert "status" in errors


@pytest.mark.asyncio
async def test_validate_filters_invalid_number(filter_manager):
    """Test validation fails for invalid number."""
    filters = {"price": "not_a_number"}

    is_valid, errors = await filter_manager.validate_filters(filters)

    assert not is_valid
    assert "price" in errors


@pytest.mark.asyncio
async def test_validate_filters_custom_validator(filter_manager):
    """Test custom validator."""
    filters = {"price": "-10"}  # Negative price should fail

    is_valid, errors = await filter_manager.validate_filters(filters)

    assert not is_valid
    assert "price" in errors


@pytest.mark.asyncio
async def test_validate_filters_unknown_field(filter_manager):
    """Test validation warns about unknown fields."""
    filters = {"unknown_field": "value"}

    is_valid, errors = await filter_manager.validate_filters(filters)

    assert not is_valid
    assert "unknown_field" in errors


def test_encode_to_url(filter_manager):
    """Test encoding filters to URL."""
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
    """Test encoding complex filter values."""
    filters = {
        "tags": ["python", "async"],
        "meta": {"key": "value"},
    }

    url = filter_manager.encode_to_url(filters)

    assert "tags" in url
    assert "meta" in url


def test_encode_to_url_skips_empty(filter_manager):
    """Test that empty values are skipped."""
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
    """Test decoding filters from URL."""
    query_string = "filter[status]=active&filter[price]=100"

    filters = filter_manager.decode_from_url(query_string)

    assert filters["status"] == "active"
    assert filters["price"] == 100  # Auto-converted to number


def test_decode_from_url_with_question_mark(filter_manager):
    """Test decoding URL with leading question mark."""
    query_string = "?filter[status]=active&filter[price]=100"

    filters = filter_manager.decode_from_url(query_string)

    assert filters["status"] == "active"
    assert filters["price"] == 100  # Auto-converted to number


def test_decode_from_url_complex_values(filter_manager):
    """Test decoding complex JSON values."""
    from lexigram.serialization import dumps_str

    tags = dumps_str(["python", "async"])
    query_string = f"filter[tags]={tags}"

    filters = filter_manager.decode_from_url(query_string)

    assert filters["tags"] == ["python", "async"]


def test_get_default_filters(filter_manager):
    """Test getting default filter values."""
    defaults = filter_manager.get_default_filters()

    assert defaults["tags"] == ""  # Has default value
    assert "status" not in defaults  # No default


@pytest.mark.asyncio
async def test_create_preset(filter_manager):
    """Test creating a filter preset."""
    filters = {"status": "active", "category": "tech"}

    preset = await filter_manager.create_preset(
        name="Active Tech",
        filters=filters,
        user_id=123,
    )

    assert preset.name == "Active Tech"
    assert preset.filters == filters
    assert preset.user_id == 123
    assert not preset.is_default
    assert preset.created_at is not None


@pytest.mark.asyncio
async def test_create_preset_default(filter_manager):
    """Test creating default preset."""
    preset = await filter_manager.create_preset(
        name="Default View",
        filters={"status": "active"},
        is_default=True,
    )

    assert preset.is_default


@pytest.mark.asyncio
async def test_get_preset(filter_manager):
    """Test retrieving a preset."""
    filters = {"status": "active"}
    await filter_manager.create_preset("My Preset", filters, user_id=123)

    preset = await filter_manager.get_preset("My Preset", user_id=123)

    assert preset is not None
    assert preset.name == "My Preset"
    assert preset.filters == filters


@pytest.mark.asyncio
async def test_get_preset_not_found(filter_manager):
    """Test getting non-existent preset."""
    preset = await filter_manager.get_preset("Not Exists")

    assert preset is None


@pytest.mark.asyncio
async def test_list_presets_user_specific(filter_manager):
    """Test listing user-specific presets."""
    await filter_manager.create_preset("User 1 Preset", {"status": "active"}, user_id=1)
    await filter_manager.create_preset(
        "User 2 Preset",
        {"status": "inactive"},
        user_id=2,
    )

    presets = await filter_manager.list_presets(user_id=1, include_shared=False)

    assert len(presets) == 1
    assert presets[0].name == "User 1 Preset"


@pytest.mark.asyncio
async def test_list_presets_shared(filter_manager):
    """Test listing shared presets."""
    await filter_manager.create_preset(
        "Shared Preset",
        {"status": "active"},
        is_shared=True,
    )

    presets = await filter_manager.list_presets(user_id=1, include_shared=True)

    assert len(presets) == 1
    assert presets[0].name == "Shared Preset"


@pytest.mark.asyncio
async def test_list_presets_global(filter_manager):
    """Test listing global presets."""
    await filter_manager.create_preset("Global Preset", {"status": "active"})

    presets = await filter_manager.list_presets()

    assert len(presets) == 1
    assert presets[0].name == "Global Preset"


@pytest.mark.asyncio
async def test_delete_preset(filter_manager):
    """Test deleting a preset."""
    await filter_manager.create_preset("To Delete", {"status": "active"}, user_id=123)

    result = await filter_manager.delete_preset("To Delete", user_id=123)

    assert result is True
    assert await filter_manager.get_preset("To Delete", user_id=123) is None


@pytest.mark.asyncio
async def test_delete_preset_not_found(filter_manager):
    """Test deleting non-existent preset."""
    result = await filter_manager.delete_preset("Not Exists")

    assert result is False


def test_get_active_filter_badges(filter_manager):
    """Test getting active filter badges."""
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
    """Test that empty filters don't create badges."""
    filters = {
        "status": "active",
        "price": "",
        "category": None,
    }

    badges = filter_manager.get_active_filter_badges(filters)

    assert len(badges) == 1
    assert badges[0]["field"] == "status"


def test_get_active_filter_badges_complex_values(filter_manager):
    """Test badges with complex values."""
    filters = {
        "tags": ["python", "async"],
    }

    badges = filter_manager.get_active_filter_badges(filters)

    assert len(badges) == 1
    assert "python, async" in badges[0]["value"]


def test_clear_all_filters(filter_manager):
    """Test clearing all filters."""
    cleared = filter_manager.clear_all_filters()

    # Should return default values
    assert cleared["tags"] == ""


def test_has_active_filters_true(filter_manager):
    """Test detecting active filters."""
    filters = {"status": "active"}

    assert filter_manager.has_active_filters(filters) is True


def test_has_active_filters_false(filter_manager):
    """Test detecting no active filters."""
    filters = {}

    assert filter_manager.has_active_filters(filters) is False


def test_has_active_filters_only_defaults(filter_manager):
    """Test that default values don't count as active."""
    filters = {"tags": ""}  # Default value

    assert filter_manager.has_active_filters(filters) is False


@pytest.mark.asyncio
async def test_apply_preset(filter_manager):
    """Test applying a saved preset."""
    filters = {"status": "active", "category": "tech"}
    await filter_manager.create_preset("My View", filters, user_id=123)

    applied = await filter_manager.apply_preset("My View", user_id=123)

    assert applied == filters


@pytest.mark.asyncio
async def test_apply_preset_not_found(filter_manager):
    """Test applying non-existent preset."""
    applied = await filter_manager.apply_preset("Not Exists")

    assert applied is None


def test_filter_definition_defaults():
    """Test FilterDefinition default values."""
    definition = FilterDefinition("test_field")

    assert definition.field == "test_field"
    assert definition.filter is None
    assert definition.label is None
    assert definition.required is False


def test_filter_preset_defaults():
    """Test FilterPreset default values."""
    preset = FilterPreset(name="Test", filters={"key": "value"})

    assert preset.name == "Test"
    assert preset.user_id is None
    assert preset.is_default is False
    assert preset.is_shared is False


def test_to_filter_set_scalar_becomes_eq(filter_manager):
    """Scalar filter values map to EQ conditions."""
    fs = filter_manager.to_filter_set({"status": "active"})

    assert len(fs["conditions"]) == 1
    assert fs["conditions"][0]["field"] == "status"
    assert fs["conditions"][0]["operator"] == "eq"
    assert fs["conditions"][0]["value"] == "active"


def test_to_filter_set_list_becomes_in(filter_manager):
    """List filter values map to IN conditions."""
    fs = filter_manager.to_filter_set({"tags": ["python", "async"]})

    assert len(fs["conditions"]) == 1
    assert fs["conditions"][0]["operator"] == "in"
    assert fs["conditions"][0]["value"] == ["python", "async"]


def test_to_filter_set_none_becomes_is_null(filter_manager):
    """None filter values map to IS_NULL conditions."""
    fs = filter_manager.to_filter_set({"deleted_at": None})

    assert len(fs["conditions"]) == 1
    assert fs["conditions"][0]["operator"] == "is_null"


def test_to_filter_set_empty_string_skipped(filter_manager):
    """Empty string filter values are dropped (same as encode_to_url)."""
    fs = filter_manager.to_filter_set({"status": "active", "price": ""})

    assert len(fs["conditions"]) == 1
    assert fs["conditions"][0]["field"] == "status"


def test_to_filter_set_pagination_forwarded(filter_manager):
    """Pagination params are forwarded to the FilterSet."""
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
    """Free-text search_query is forwarded to the FilterSet."""
    fs = filter_manager.to_filter_set({"status": "active"}, search_query="hello")

    assert fs["search_query"] == "hello"


def test_to_search_query_returns_search_query(filter_manager):
    """to_search_query() requires an injected translator."""
    with pytest.raises(RuntimeError):
        filter_manager.to_search_query({"status": "active"}, search_query="test")


def test_to_search_query_custom_translator(filter_definitions):
    """Custom FilterSetTranslator injected via constructor is used."""
    from unittest.mock import MagicMock

    mock_translator = MagicMock()
    mock_translator.translate.return_value = {"q": "mocked"}

    fm = FilterManager(filter_definitions, translator=mock_translator)
    sq = fm.to_search_query({"status": "active"})

    mock_translator.translate.assert_called_once()
    assert sq["q"] == "mocked"


def test_round_trip_url_encoding(filter_manager):
    """Test encoding and decoding filters maintains values."""
    original_filters = {
        "status": "active",
        "price": 100,  # Already a number
        "category": "tech",
    }

    # Encode to URL
    url = filter_manager.encode_to_url(original_filters)

    # Decode back
    decoded_filters = filter_manager.decode_from_url(url)

    assert decoded_filters == original_filters
