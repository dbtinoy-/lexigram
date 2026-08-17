"""Tests for SavedFiltersService."""

from __future__ import annotations

import pytest

from lexigram.admin.services.saved_filters import SavedFilterSet, SavedFiltersService


class TestSavedFiltersService:
    """Core saved filter operations using in-memory store."""

    def _make_svc(self, **kwargs) -> SavedFiltersService:
        return SavedFiltersService(**kwargs)

    @pytest.mark.asyncio
    async def test_save_and_list(self) -> None:
        svc = self._make_svc()
        result = await svc.save("users", "Active Admins", {"role": "admin", "is_active": "1"}, user_id="u1")

        assert result.is_ok()
        saved = result.unwrap()
        assert saved.resource == "users"
        assert saved.name == "Active Admins"
        assert saved.filters == {"role": "admin", "is_active": "1"}

        sets = await svc.list_for_resource("users", user_id="u1")
        assert len(sets) == 1
        assert sets[0].name == "Active Admins"

    @pytest.mark.asyncio
    async def test_save_empty_name_errors(self) -> None:
        svc = self._make_svc()
        result = await svc.save("users", "  ", {"role": "admin"}, user_id="u1")
        assert result.is_err()

    @pytest.mark.asyncio
    async def test_save_empty_filters_errors(self) -> None:
        svc = self._make_svc()
        result = await svc.save("users", "My Filter", {}, user_id="u1")
        assert result.is_err()

    @pytest.mark.asyncio
    async def test_save_overwrites_existing_same_name(self) -> None:
        svc = self._make_svc()
        await svc.save("users", "My Filter", {"role": "admin"}, user_id="u1")
        await svc.save("users", "My Filter", {"role": "super"}, user_id="u1")

        sets = await svc.list_for_resource("users", user_id="u1")
        assert len(sets) == 1
        assert sets[0].filters["role"] == "super"

    @pytest.mark.asyncio
    async def test_list_includes_global_presets(self) -> None:
        svc = self._make_svc()
        await svc.save("users", "Global Filter", {"is_active": "1"}, user_id=None)
        await svc.save("users", "My Filter", {"role": "admin"}, user_id="u1")

        sets = await svc.list_for_resource("users", user_id="u1")
        names = {s.name for s in sets}
        assert "Global Filter" in names
        assert "My Filter" in names

    @pytest.mark.asyncio
    async def test_list_sorted_by_name(self) -> None:
        svc = self._make_svc()
        await svc.save("users", "Zebra", {"a": "1"}, user_id="u1")
        await svc.save("users", "Apple", {"b": "2"}, user_id="u1")

        sets = await svc.list_for_resource("users", user_id="u1")
        assert sets[0].name == "Apple"
        assert sets[1].name == "Zebra"

    @pytest.mark.asyncio
    async def test_list_isolated_by_resource(self) -> None:
        svc = self._make_svc()
        await svc.save("users", "Filter A", {"x": "1"}, user_id="u1")
        await svc.save("posts", "Filter B", {"y": "2"}, user_id="u1")

        user_sets = await svc.list_for_resource("users", user_id="u1")
        post_sets = await svc.list_for_resource("posts", user_id="u1")

        assert len(user_sets) == 1
        assert user_sets[0].name == "Filter A"
        assert len(post_sets) == 1
        assert post_sets[0].name == "Filter B"

    @pytest.mark.asyncio
    async def test_delete_existing(self) -> None:
        svc = self._make_svc()
        await svc.save("users", "My Filter", {"role": "admin"}, user_id="u1")

        result = await svc.delete("users", "My Filter", user_id="u1")
        assert result.is_ok()

        sets = await svc.list_for_resource("users", user_id="u1")
        assert sets == []

    @pytest.mark.asyncio
    async def test_delete_not_found(self) -> None:
        svc = self._make_svc()
        result = await svc.delete("users", "Nonexistent", user_id="u1")
        assert result.is_err()

    @pytest.mark.asyncio
    async def test_max_per_user_per_resource_enforced(self) -> None:
        svc = self._make_svc(max_per_user_per_resource=2)
        await svc.save("users", "Filter 1", {"a": "1"}, user_id="u1")
        await svc.save("users", "Filter 2", {"b": "2"}, user_id="u1")

        result = await svc.save("users", "Filter 3", {"c": "3"}, user_id="u1")
        assert result.is_err()
        assert "Maximum" in result.unwrap_err().message

    @pytest.mark.asyncio
    async def test_max_does_not_block_overwrite(self) -> None:
        svc = self._make_svc(max_per_user_per_resource=2)
        await svc.save("users", "Filter 1", {"a": "1"}, user_id="u1")
        await svc.save("users", "Filter 2", {"b": "2"}, user_id="u1")

        # Overwriting Filter 1 should succeed even at the limit
        result = await svc.save("users", "Filter 1", {"a": "updated"}, user_id="u1")
        assert result.is_ok()


class TestSavedFilterSet:
    """Unit tests for SavedFilterSet dataclass."""

    def test_frozen(self) -> None:
        s = SavedFilterSet(resource="users", name="x", filters={"k": "v"})
        with pytest.raises((AttributeError, TypeError)):
            s.name = "changed"  # type: ignore[misc]
