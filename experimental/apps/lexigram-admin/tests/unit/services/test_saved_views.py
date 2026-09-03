"""SavedViewService tests (R13 — docs/09-01-2026/08-saved-views.md)."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.services.saved_views import (
    MAX_VIEWS_PER_RESOURCE,
    SavedViewError,
    SavedViewService,
)


class _FakeSettings:
    """In-memory stand-in for AdminSettingsService."""

    def __init__(self) -> None:
        self.data: dict[tuple[str, str], Any] = {}
        self.fail_get = False
        self.fail_set = False

    async def get(self, tenant_id: str, name: str) -> Any:
        if self.fail_get:
            raise RuntimeError("db down")
        return self.data.get((tenant_id, name))

    async def set(self, tenant_id: str, name: str, value: Any) -> None:
        if self.fail_set:
            raise RuntimeError("db down")
        self.data[(tenant_id, name)] = value


@pytest.fixture
def settings() -> _FakeSettings:
    return _FakeSettings()


@pytest.fixture
def service(settings: _FakeSettings) -> SavedViewService:
    return SavedViewService(settings)


class TestSanitizeQuery:
    def test_keeps_whitelisted_params(self) -> None:
        query = "search=abc&per_page=50&sort_by=name&sort_order=desc&density=compact"
        assert SavedViewService.sanitize_query(query) == query

    def test_keeps_filter_params(self) -> None:
        assert (
            SavedViewService.sanitize_query("filter_status=active&filter_role=admin")
            == "filter_status=active&filter_role=admin"
        )

    def test_drops_volatile_and_unknown_params(self) -> None:
        result = SavedViewService.sanitize_query(
            "page=3&cursor=xyz&notice=saved&error=no&evil=1&search=a"
        )
        assert result == "search=a"

    def test_canonicalizes_legacy_aliases(self) -> None:
        result = SavedViewService.sanitize_query("q=abc&sort=name&dir=desc")
        assert result == "search=abc&sort_by=name&sort_order=desc"

    def test_order_alias_maps_to_sort_order(self) -> None:
        assert (
            SavedViewService.sanitize_query("order=asc&sort=email")
            == "sort_order=asc&sort_by=email"
        )

    def test_first_value_wins_on_duplicates(self) -> None:
        assert SavedViewService.sanitize_query("search=a&search=b") == "search=a"

    def test_leading_question_mark_and_empty(self) -> None:
        assert SavedViewService.sanitize_query("?search=a") == "search=a"
        assert SavedViewService.sanitize_query("") == ""
        assert SavedViewService.sanitize_query("?") == ""

    def test_drops_blank_values(self) -> None:
        assert SavedViewService.sanitize_query("search=&sort_by=name") == (
            "sort_by=name"
        )

    def test_bare_filter_prefix_is_not_allowed(self) -> None:
        assert SavedViewService.sanitize_query("filter_=x") == ""

    def test_reencodes_special_characters(self) -> None:
        result = SavedViewService.sanitize_query("search=a%20b%26c")
        assert result == "search=a+b%26c"


class TestSaveView:
    @pytest.mark.asyncio
    async def test_save_and_list_roundtrip(self, service: SavedViewService) -> None:
        entry = await service.save_view(
            "u-1", "users", "Active", "filter_status=active"
        )
        assert entry["name"] == "Active"
        assert entry["query"] == "filter_status=active"
        views = await service.list_views("u-1", "users")
        assert [v["name"] for v in views] == ["Active"]

    @pytest.mark.asyncio
    async def test_save_sanitizes_query(self, service: SavedViewService) -> None:
        entry = await service.save_view(
            "u-1", "users", "V", "page=9&cursor=z&q=abc&junk=1"
        )
        assert entry["query"] == "search=abc"

    @pytest.mark.asyncio
    async def test_upsert_by_case_insensitive_name(
        self, service: SavedViewService
    ) -> None:
        await service.save_view("u-1", "users", "Mine", "search=a")
        await service.save_view("u-1", "users", "mine", "search=b")
        views = await service.list_views("u-1", "users")
        assert len(views) == 1
        assert views[0]["query"] == "search=b"

    @pytest.mark.asyncio
    async def test_views_sorted_by_name(self, service: SavedViewService) -> None:
        await service.save_view("u-1", "users", "zeta", "search=z")
        await service.save_view("u-1", "users", "Alpha", "search=a")
        views = await service.list_views("u-1", "users")
        assert [v["name"] for v in views] == ["Alpha", "zeta"]

    @pytest.mark.asyncio
    async def test_scoped_per_user_and_resource(
        self, service: SavedViewService
    ) -> None:
        await service.save_view("u-1", "users", "Mine", "search=a")
        assert await service.list_views("u-2", "users") == []
        assert await service.list_views("u-1", "posts") == []

    @pytest.mark.asyncio
    async def test_empty_sanitized_query_rejected(
        self, service: SavedViewService
    ) -> None:
        with pytest.raises(SavedViewError, match="Nothing to save"):
            await service.save_view("u-1", "users", "V", "page=2&junk=1")

    @pytest.mark.asyncio
    async def test_name_required_and_length_capped(
        self, service: SavedViewService
    ) -> None:
        with pytest.raises(SavedViewError, match="name is required"):
            await service.save_view("u-1", "users", "   ", "search=a")
        with pytest.raises(SavedViewError, match="at most 64"):
            await service.save_view("u-1", "users", "x" * 65, "search=a")

    @pytest.mark.asyncio
    async def test_control_characters_stripped_from_name(
        self, service: SavedViewService
    ) -> None:
        entry = await service.save_view("u-1", "users", "My\x00\x1fView", "search=a")
        assert entry["name"] == "MyView"

    @pytest.mark.asyncio
    async def test_invalid_resource_rejected(self, service: SavedViewService) -> None:
        for bad in ("", "Users", "a b", "../etc", "x" * 65):
            with pytest.raises(SavedViewError, match="Invalid resource"):
                await service.save_view("u-1", bad, "V", "search=a")

    @pytest.mark.asyncio
    async def test_guest_and_empty_user_rejected(
        self, service: SavedViewService
    ) -> None:
        for bad_user in ("", "guest"):
            with pytest.raises(SavedViewError, match="signed-in user"):
                await service.save_view(bad_user, "users", "V", "search=a")

    @pytest.mark.asyncio
    async def test_view_count_cap(self, service: SavedViewService) -> None:
        for i in range(MAX_VIEWS_PER_RESOURCE):
            await service.save_view("u-1", "users", f"view-{i:02d}", "search=a")
        with pytest.raises(SavedViewError, match="Limit of"):
            await service.save_view("u-1", "users", "one-too-many", "search=a")
        # Upsert of an existing name is still allowed at the cap.
        await service.save_view("u-1", "users", "view-00", "search=b")

    @pytest.mark.asyncio
    async def test_none_settings_service_raises(self) -> None:
        service = SavedViewService(None)
        with pytest.raises(SavedViewError, match="unavailable"):
            await service.save_view("u-1", "users", "V", "search=a")

    @pytest.mark.asyncio
    async def test_write_failure_surfaces_friendly_error(
        self, service: SavedViewService, settings: _FakeSettings
    ) -> None:
        settings.fail_set = True
        with pytest.raises(SavedViewError, match="try again"):
            await service.save_view("u-1", "users", "V", "search=a")

    @pytest.mark.asyncio
    async def test_upsert_preserves_created_at(
        self, service: SavedViewService, settings: _FakeSettings
    ) -> None:
        first = await service.save_view("u-1", "users", "V", "search=a")
        second = await service.save_view("u-1", "users", "V", "search=b")
        assert second["created_at"] == first["created_at"]


class TestListViews:
    @pytest.mark.asyncio
    async def test_empty_by_default(self, service: SavedViewService) -> None:
        assert await service.list_views("u-1", "users") == []

    @pytest.mark.asyncio
    async def test_none_settings_service_returns_empty(self) -> None:
        assert await SavedViewService(None).list_views("u-1", "users") == []

    @pytest.mark.asyncio
    async def test_invalid_inputs_return_empty(self, service: SavedViewService) -> None:
        assert await service.list_views("guest", "users") == []
        assert await service.list_views("u-1", "Bad Resource") == []

    @pytest.mark.asyncio
    async def test_read_failure_degrades_to_empty(
        self, service: SavedViewService, settings: _FakeSettings
    ) -> None:
        settings.fail_get = True
        assert await service.list_views("u-1", "users") == []

    @pytest.mark.asyncio
    async def test_corrupt_payload_tolerated(
        self, service: SavedViewService, settings: _FakeSettings
    ) -> None:
        settings.data[("default", "saved_views.u-1.users")] = [
            "not-a-dict",
            {"query": "search=a"},  # missing name → skipped
            {"name": "Good", "query": "search=a"},
            42,
        ]
        views = await service.list_views("u-1", "users")
        assert [v["name"] for v in views] == ["Good"]

    @pytest.mark.asyncio
    async def test_non_list_payload_tolerated(
        self, service: SavedViewService, settings: _FakeSettings
    ) -> None:
        settings.data[("default", "saved_views.u-1.users")] = {"oops": True}
        assert await service.list_views("u-1", "users") == []


class TestDefaultView:
    @pytest.mark.asyncio
    async def test_legacy_view_is_not_default(self, service: SavedViewService) -> None:
        await service.save_view("u-1", "users", "Mine", "search=a")
        views = await service.list_views("u-1", "users")
        assert views[0]["default"] is False
        assert await service.get_default_view("u-1", "users") is None

    @pytest.mark.asyncio
    async def test_set_default_returns_sanitized_entry(
        self, service: SavedViewService
    ) -> None:
        await service.save_view("u-1", "users", "Mine", "search=a&page=4")
        assert await service.set_default_view("u-1", "users", "Mine") is True
        default = await service.get_default_view("u-1", "users")
        assert default is not None
        assert default["name"] == "Mine"
        assert default["query"] == "search=a"
        assert default["default"] is True

    @pytest.mark.asyncio
    async def test_setting_another_default_replaces_the_old_one(
        self, service: SavedViewService
    ) -> None:
        await service.save_view("u-1", "users", "Mine", "search=a")
        await service.save_view("u-1", "users", "Other", "search=b")
        await service.set_default_view("u-1", "users", "Mine")
        await service.set_default_view("u-1", "users", "OTHER")
        views = await service.list_views("u-1", "users")
        assert [(v["name"], v["default"]) for v in views] == [
            ("Mine", False),
            ("Other", True),
        ]

    @pytest.mark.asyncio
    async def test_upsert_preserves_default_marker(
        self, service: SavedViewService
    ) -> None:
        await service.save_view("u-1", "users", "Mine", "search=a")
        await service.set_default_view("u-1", "users", "Mine")
        await service.save_view("u-1", "users", "mine", "search=b")
        default = await service.get_default_view("u-1", "users")
        assert default is not None
        assert default["query"] == "search=b"

    @pytest.mark.asyncio
    async def test_clear_default_is_idempotent(self, service: SavedViewService) -> None:
        await service.save_view("u-1", "users", "Mine", "search=a")
        assert await service.set_default_view("u-1", "users", None) is False
        await service.set_default_view("u-1", "users", "Mine")
        assert await service.set_default_view("u-1", "users", None) is True
        assert await service.get_default_view("u-1", "users") is None
        assert await service.set_default_view("u-1", "users", None) is False

    @pytest.mark.asyncio
    async def test_missing_default_target_errors(
        self, service: SavedViewService
    ) -> None:
        with pytest.raises(SavedViewError, match="not found"):
            await service.set_default_view("u-1", "users", "Missing")

    @pytest.mark.asyncio
    async def test_corrupt_multiple_defaults_choose_first_valid(
        self, service: SavedViewService, settings: _FakeSettings
    ) -> None:
        settings.data[("default", "saved_views.u-1.users")] = [
            {"name": "Empty", "query": "page=4", "default": True},
            {"name": "Good", "query": "search=ok", "default": True},
            {"name": "StringFlag", "query": "search=no", "default": "false"},
        ]
        views = await service.list_views("u-1", "users")
        assert [(v["name"], v["default"]) for v in views] == [
            ("Empty", False),
            ("Good", True),
            ("StringFlag", False),
        ]
        default = await service.get_default_view("u-1", "users")
        assert default is not None
        assert default["name"] == "Good"

    @pytest.mark.asyncio
    async def test_default_read_failure_is_friendly(
        self, service: SavedViewService, settings: _FakeSettings
    ) -> None:
        settings.fail_get = True
        with pytest.raises(SavedViewError, match="update the default"):
            await service.set_default_view("u-1", "users", "Mine")

    @pytest.mark.asyncio
    async def test_default_write_failure_is_friendly(
        self, service: SavedViewService, settings: _FakeSettings
    ) -> None:
        await service.save_view("u-1", "users", "Mine", "search=a")
        settings.fail_set = True
        with pytest.raises(SavedViewError, match="update the default"):
            await service.set_default_view("u-1", "users", "Mine")


class TestDeleteView:
    @pytest.mark.asyncio
    async def test_delete_existing(self, service: SavedViewService) -> None:
        await service.save_view("u-1", "users", "Mine", "search=a")
        assert await service.delete_view("u-1", "users", "MINE") is True
        assert await service.list_views("u-1", "users") == []

    @pytest.mark.asyncio
    async def test_delete_missing_returns_false(
        self, service: SavedViewService
    ) -> None:
        assert await service.delete_view("u-1", "users", "Nope") is False

    @pytest.mark.asyncio
    async def test_delete_only_named_view(self, service: SavedViewService) -> None:
        await service.save_view("u-1", "users", "Keep", "search=a")
        await service.save_view("u-1", "users", "Drop", "search=b")
        assert await service.delete_view("u-1", "users", "Drop") is True
        views = await service.list_views("u-1", "users")
        assert [v["name"] for v in views] == ["Keep"]

    @pytest.mark.asyncio
    async def test_none_settings_service_raises(self) -> None:
        with pytest.raises(SavedViewError, match="unavailable"):
            await SavedViewService(None).delete_view("u-1", "users", "V")

    @pytest.mark.asyncio
    async def test_write_failure_surfaces_friendly_error(
        self, service: SavedViewService, settings: _FakeSettings
    ) -> None:
        await service.save_view("u-1", "users", "V", "search=a")
        settings.fail_set = True
        with pytest.raises(SavedViewError, match="try again"):
            await service.delete_view("u-1", "users", "V")
