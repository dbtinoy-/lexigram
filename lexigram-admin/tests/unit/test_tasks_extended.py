"""Tests for tasks/bulk_operations.py — async task functions and AdminTaskResult."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from lexigram.admin.tasks.bulk_operations import (
    AdminTaskResult,
    bulk_delete_task,
    bulk_import_task,
    bulk_update_task,
    cache_warm_task,
    data_cleanup_task,
)


class TestAdminTaskResult:
    """Tests for AdminTaskResult dataclass."""

    def test_defaults(self) -> None:
        result = AdminTaskResult(success=True)
        assert result.success is True
        assert result.message == ""
        assert result.data == {}
        assert result.errors == []
        assert result.warnings == []

    def test_to_dict(self) -> None:
        result = AdminTaskResult(
            success=False,
            message="Something failed",
            data={"count": 0},
            errors=["Error 1", "Error 2"],
            warnings=["Warn 1"],
        )
        d = result.to_dict()
        assert d["success"] is False
        assert d["message"] == "Something failed"
        assert d["data"] == {"count": 0}
        assert d["errors"] == ["Error 1", "Error 2"]
        assert d["warnings"] == ["Warn 1"]

    def test_to_dict_success(self) -> None:
        result = AdminTaskResult(success=True, message="Done")
        d = result.to_dict()
        assert d["success"] is True
        assert d["message"] == "Done"


class TestBulkImportTask:
    """Tests for bulk_import_task."""

    @pytest.mark.asyncio
    async def test_file_not_found(self) -> None:
        result = await bulk_import_task(
            resource_type="users",
            file_path="/nonexistent/path/file.csv",
            file_format="csv",
        )
        assert result.success is False
        assert "not found" in result.message.lower() or "File not found" in result.errors

    @pytest.mark.asyncio
    async def test_existing_file_succeeds(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            f.write(b"id,name\n1,Alice\n")
            tmp_path = f.name

        try:
            result = await bulk_import_task(
                resource_type="users",
                file_path=tmp_path,
                file_format="csv",
                user_id="admin",
            )
            assert result.success is True
            assert "data" in result.to_dict()
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_with_mapping(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            f.write(b'[{"name": "Alice"}]')
            tmp_path = f.name

        try:
            result = await bulk_import_task(
                resource_type="users",
                file_path=tmp_path,
                file_format="json",
                mapping={"name": "full_name"},
                on_duplicate="skip",
            )
            assert result.success is True
        finally:
            Path(tmp_path).unlink(missing_ok=True)


class TestBulkUpdateTask:
    """Tests for bulk_update_task."""

    @pytest.mark.asyncio
    async def test_empty_ids(self) -> None:
        result = await bulk_update_task(
            resource_type="users",
            resource_ids=[],
            data={"status": "active"},
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_with_ids(self) -> None:
        result = await bulk_update_task(
            resource_type="posts",
            resource_ids=["p1", "p2", "p3"],
            data={"published": True},
            user_id="admin",
        )
        assert result.success is True
        d = result.to_dict()
        assert "data" in d
        assert d["data"]["updated"] == 0  # Placeholder impl

    @pytest.mark.asyncio
    async def test_returns_result_with_counts(self) -> None:
        result = await bulk_update_task(
            resource_type="users",
            resource_ids=["u1"],
            data={"is_active": False},
        )
        assert result.success is True
        assert "updated" in result.data
        assert "failed" in result.data


class TestBulkDeleteTask:
    """Tests for bulk_delete_task."""

    @pytest.mark.asyncio
    async def test_soft_delete(self) -> None:
        result = await bulk_delete_task(
            resource_type="users",
            resource_ids=["u1", "u2"],
            soft_delete=True,
            user_id="admin",
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_hard_delete(self) -> None:
        result = await bulk_delete_task(
            resource_type="posts",
            resource_ids=["p1"],
            soft_delete=False,
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_empty_ids(self) -> None:
        result = await bulk_delete_task(
            resource_type="comments",
            resource_ids=[],
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_returns_counts(self) -> None:
        result = await bulk_delete_task(
            resource_type="tags",
            resource_ids=["t1"],
        )
        assert "deleted" in result.data
        assert "failed" in result.data


class TestDataCleanupTask:
    """Tests for data_cleanup_task."""

    @pytest.mark.asyncio
    async def test_default_cleanup(self) -> None:
        result = await data_cleanup_task()
        assert result.success is True
        assert "cleaned" in result.data

    @pytest.mark.asyncio
    async def test_cleanup_specific_resource(self) -> None:
        result = await data_cleanup_task(
            resource_type="audit_logs",
            older_than_days=30,
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_cleanup_returns_count(self) -> None:
        result = await data_cleanup_task(older_than_days=90)
        assert result.data["cleaned"] == 0  # Placeholder


class TestCacheWarmTask:
    """Tests for cache_warm_task."""

    @pytest.mark.asyncio
    async def test_warm_all(self) -> None:
        result = await cache_warm_task()
        assert result.success is True
        assert "warmed" in result.data

    @pytest.mark.asyncio
    async def test_warm_specific_resources(self) -> None:
        result = await cache_warm_task(resource_types=["users", "posts"])
        assert result.success is True

    @pytest.mark.asyncio
    async def test_warm_returns_count(self) -> None:
        result = await cache_warm_task()
        assert result.data["warmed"] == 0  # Placeholder
