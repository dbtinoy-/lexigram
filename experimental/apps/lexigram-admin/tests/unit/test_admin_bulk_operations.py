"""Tests for admin bulk operations types."""

import pytest

from lexigram.admin.tasks.bulk_operations import AdminTaskType, TaskProgress


class TestAdminTaskType:
    """Tests for AdminTaskType enum."""

    def test_admin_task_type_values(self) -> None:
        """Test AdminTaskType enum values."""
        assert AdminTaskType.BULK_EXPORT.value == "admin.bulk_export"
        assert AdminTaskType.BULK_IMPORT.value == "admin.bulk_import"
        assert AdminTaskType.BULK_UPDATE.value == "admin.bulk_update"
        assert AdminTaskType.BULK_DELETE.value == "admin.bulk_delete"
        assert AdminTaskType.REPORT_GENERATION.value == "admin.report_generation"
        assert AdminTaskType.DATA_CLEANUP.value == "admin.data_cleanup"
        assert AdminTaskType.CACHE_WARM.value == "admin.cache_warm"
        assert AdminTaskType.INDEX_REBUILD.value == "admin.index_rebuild"

    def test_admin_task_type_members(self) -> None:
        """Test AdminTaskType has expected members."""
        members = list(AdminTaskType)
        assert len(members) == 8


class TestTaskProgress:
    """Tests for TaskProgress dataclass."""

    def test_task_progress_defaults(self) -> None:
        """Test TaskProgress default values."""
        progress = TaskProgress()
        assert progress.total == 0
        assert progress.completed == 0
        assert progress.failed == 0
        assert progress.current_item is None
        assert progress.message == ""

    def test_task_progress_percentage_zero(self) -> None:
        """Test TaskProgress percentage when total is 0."""
        progress = TaskProgress()
        assert progress.percentage == 0

    def test_task_progress_percentage_calculation(self) -> None:
        """Test TaskProgress percentage calculation."""
        progress = TaskProgress(total=100, completed=50)
        assert progress.percentage == 50

    def test_task_progress_percentage_full(self) -> None:
        """Test TaskProgress percentage when complete."""
        progress = TaskProgress(total=100, completed=100)
        assert progress.percentage == 100

    def test_task_progress_to_dict(self) -> None:
        """Test TaskProgress to_dict."""
        progress = TaskProgress(
            total=100,
            completed=50,
            failed=5,
            current_item="item-50",
            message="Processing...",
        )
        d = progress.to_dict()
        assert d["total"] == 100
        assert d["completed"] == 50
        assert d["failed"] == 5
        assert d["percentage"] == 50
