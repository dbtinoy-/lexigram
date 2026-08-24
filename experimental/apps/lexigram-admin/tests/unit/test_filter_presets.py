"""Tests for filter preset operations."""

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
async def test_create_preset(filter_manager):
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
    preset = await filter_manager.create_preset(
        name="Default View",
        filters={"status": "active"},
        is_default=True,
    )
    assert preset.is_default


@pytest.mark.asyncio
async def test_get_preset(filter_manager):
    filters = {"status": "active"}
    await filter_manager.create_preset("My Preset", filters, user_id=123)
    preset = await filter_manager.get_preset("My Preset", user_id=123)
    assert preset is not None
    assert preset.name == "My Preset"
    assert preset.filters == filters


@pytest.mark.asyncio
async def test_get_preset_not_found(filter_manager):
    preset = await filter_manager.get_preset("Not Exists")
    assert preset is None


@pytest.mark.asyncio
async def test_list_presets_user_specific(filter_manager):
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
    await filter_manager.create_preset("Global Preset", {"status": "active"})
    presets = await filter_manager.list_presets()
    assert len(presets) == 1
    assert presets[0].name == "Global Preset"


@pytest.mark.asyncio
async def test_delete_preset(filter_manager):
    await filter_manager.create_preset("To Delete", {"status": "active"}, user_id=123)
    result = await filter_manager.delete_preset("To Delete", user_id=123)
    assert result is True
    assert await filter_manager.get_preset("To Delete", user_id=123) is None


@pytest.mark.asyncio
async def test_delete_preset_not_found(filter_manager):
    result = await filter_manager.delete_preset("Not Exists")
    assert result is False


@pytest.mark.asyncio
async def test_apply_preset(filter_manager):
    filters = {"status": "active", "category": "tech"}
    await filter_manager.create_preset("My View", filters, user_id=123)
    applied = await filter_manager.apply_preset("My View", user_id=123)
    assert applied == filters


@pytest.mark.asyncio
async def test_apply_preset_not_found(filter_manager):
    applied = await filter_manager.apply_preset("Not Exists")
    assert applied is None
