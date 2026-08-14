"""Tests for RevisionService — snapshot, diff and revert."""

from __future__ import annotations

import pytest

from lexigram.admin.services.revisions import (
    InMemoryRevisionStore,
    RevisionService,
)


class TestRevisionServiceBasics:
    @pytest.mark.asyncio
    async def test_record_creates_revision(self) -> None:
        svc = RevisionService()
        rev = await svc.record("user", "u1", {"name": "Alice", "email": "a@b.com"})

        assert rev.resource_type == "user"
        assert rev.resource_id == "u1"
        assert rev.data == {"name": "Alice", "email": "a@b.com"}
        assert rev.revision_id.startswith("rev-")

    @pytest.mark.asyncio
    async def test_list_revisions_newest_first(self) -> None:
        svc = RevisionService()
        await svc.record("user", "u1", {"v": 1})
        await svc.record("user", "u1", {"v": 2})
        await svc.record("user", "u1", {"v": 3})

        revisions = await svc.list_revisions("user", "u1")
        assert len(revisions) == 3
        assert revisions[0].data["v"] == 3
        assert revisions[-1].data["v"] == 1

    @pytest.mark.asyncio
    async def test_list_respects_limit(self) -> None:
        svc = RevisionService()
        for i in range(10):
            await svc.record("product", "p1", {"i": i})
        revisions = await svc.list_revisions("product", "p1", limit=3)
        assert len(revisions) == 3

    @pytest.mark.asyncio
    async def test_get_revision_returns_by_id(self) -> None:
        svc = RevisionService()
        rev = await svc.record("user", "u1", {"name": "Bob"})
        fetched = await svc.get_revision(rev.revision_id)

        assert fetched is not None
        assert fetched.revision_id == rev.revision_id

    @pytest.mark.asyncio
    async def test_get_revision_returns_none_for_missing(self) -> None:
        svc = RevisionService()
        result = await svc.get_revision("nonexistent-rev")
        assert result is None


class TestRevisionDiff:
    @pytest.mark.asyncio
    async def test_diff_detects_changed_fields(self) -> None:
        svc = RevisionService()
        rev_a = await svc.record("user", "u1", {"name": "Alice", "email": "a@b.com", "role": "user"})
        rev_b = await svc.record("user", "u1", {"name": "Alicia", "email": "a@b.com", "role": "admin"})

        diff = await svc.diff(rev_a.revision_id, rev_b.revision_id)

        assert diff is not None
        changed_fields = {d.field_name for d in diff.fields}
        assert "name" in changed_fields
        assert "role" in changed_fields
        assert "email" not in changed_fields  # unchanged — excluded by default

    @pytest.mark.asyncio
    async def test_diff_include_unchanged(self) -> None:
        svc = RevisionService()
        rev_a = await svc.record("user", "u1", {"name": "Alice", "email": "a@b.com"})
        rev_b = await svc.record("user", "u1", {"name": "Bob", "email": "a@b.com"})

        diff = await svc.diff(rev_a.revision_id, rev_b.revision_id, include_unchanged=True)

        assert diff is not None
        assert diff.all_fields is True
        all_fields = {d.field_name for d in diff.fields}
        assert "name" in all_fields
        assert "email" in all_fields

    @pytest.mark.asyncio
    async def test_diff_field_values_correct(self) -> None:
        svc = RevisionService()
        rev_a = await svc.record("order", "o1", {"status": "pending"})
        rev_b = await svc.record("order", "o1", {"status": "shipped"})

        diff = await svc.diff(rev_a.revision_id, rev_b.revision_id)
        assert diff is not None

        status_diff = next(d for d in diff.fields if d.field_name == "status")
        assert status_diff.old_value == "pending"
        assert status_diff.new_value == "shipped"
        assert status_diff.changed is True

    @pytest.mark.asyncio
    async def test_diff_returns_none_if_revision_missing(self) -> None:
        svc = RevisionService()
        rev = await svc.record("user", "u1", {"x": 1})
        result = await svc.diff(rev.revision_id, "ghost-rev")
        assert result is None

    @pytest.mark.asyncio
    async def test_diff_detects_added_field(self) -> None:
        svc = RevisionService()
        rev_a = await svc.record("user", "u1", {"name": "Alice"})
        rev_b = await svc.record("user", "u1", {"name": "Alice", "phone": "+1234"})

        diff = await svc.diff(rev_a.revision_id, rev_b.revision_id)
        assert diff is not None

        phone_diff = next(d for d in diff.fields if d.field_name == "phone")
        assert phone_diff.old_value is None
        assert phone_diff.new_value == "+1234"

    @pytest.mark.asyncio
    async def test_diff_detects_removed_field(self) -> None:
        svc = RevisionService()
        rev_a = await svc.record("user", "u1", {"name": "Alice", "phone": "+1234"})
        rev_b = await svc.record("user", "u1", {"name": "Alice"})

        diff = await svc.diff(rev_a.revision_id, rev_b.revision_id)
        assert diff is not None

        phone_diff = next(d for d in diff.fields if d.field_name == "phone")
        assert phone_diff.old_value == "+1234"
        assert phone_diff.new_value is None


class TestRevisionRevert:
    @pytest.mark.asyncio
    async def test_revert_data_returns_snapshot(self) -> None:
        svc = RevisionService()
        rev = await svc.record("user", "u1", {"name": "Alice", "role": "admin"})

        data = await svc.revert_data(rev.revision_id)

        assert data == {"name": "Alice", "role": "admin"}

    @pytest.mark.asyncio
    async def test_revert_data_is_copy(self) -> None:
        svc = RevisionService()
        original = {"name": "Alice"}
        rev = await svc.record("user", "u1", original)

        data = await svc.revert_data(rev.revision_id)
        assert data is not None
        data["name"] = "Mutated"

        # Original revision data should not be affected
        rev2 = await svc.get_revision(rev.revision_id)
        assert rev2 is not None
        assert rev2.data["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_revert_data_none_for_missing(self) -> None:
        svc = RevisionService()
        result = await svc.revert_data("nonexistent")
        assert result is None


class TestRevisionPurge:
    @pytest.mark.asyncio
    async def test_purge_deletes_all_revisions(self) -> None:
        svc = RevisionService()
        await svc.record("user", "u1", {"v": 1})
        await svc.record("user", "u1", {"v": 2})

        deleted = await svc.purge("user", "u1")

        assert deleted == 2
        revisions = await svc.list_revisions("user", "u1")
        assert revisions == []

    @pytest.mark.asyncio
    async def test_purge_only_affects_target_record(self) -> None:
        svc = RevisionService()
        await svc.record("user", "u1", {"v": 1})
        await svc.record("user", "u2", {"v": 1})

        await svc.purge("user", "u1")

        u2_revisions = await svc.list_revisions("user", "u2")
        assert len(u2_revisions) == 1


class TestInMemoryRevisionStore:
    @pytest.mark.asyncio
    async def test_max_per_record_trims_oldest(self) -> None:
        store = InMemoryRevisionStore(max_per_record=3)
        svc = RevisionService(store=store)

        for i in range(5):
            await svc.record("item", "i1", {"v": i})

        revisions = await svc.list_revisions("item", "i1")
        assert len(revisions) == 3
        assert revisions[0].data["v"] == 4  # newest

    @pytest.mark.asyncio
    async def test_store_isolates_different_resource_types(self) -> None:
        svc = RevisionService()
        await svc.record("user", "1", {"name": "Alice"})
        await svc.record("product", "1", {"name": "Widget"})

        user_revs = await svc.list_revisions("user", "1")
        product_revs = await svc.list_revisions("product", "1")

        assert len(user_revs) == 1
        assert len(product_revs) == 1
        assert user_revs[0].data["name"] == "Alice"
        assert product_revs[0].data["name"] == "Widget"
