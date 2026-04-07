"""Tests for admin storage types."""

from datetime import datetime, timezone

from lexigram.admin.services.storage.types import (
    AdminFileInfo,
    AdminUploadOptions,
    StorageDriver,
    UploadResult,
)


class TestStorageDriver:
    """Tests for StorageDriver enum."""

    def test_storage_driver_values(self) -> None:
        """Test StorageDriver enum values."""
        assert StorageDriver.LOCAL.value == "local"
        assert StorageDriver.S3.value == "s3"
        assert StorageDriver.MEMORY.value == "memory"

    def test_storage_driver_members(self) -> None:
        """Test StorageDriver has expected members."""
        members = list(StorageDriver)
        assert len(members) == 3

    def test_storage_driver_from_string(self) -> None:
        """Test creating StorageDriver from string."""
        assert StorageDriver("local") == StorageDriver.LOCAL
        assert StorageDriver("s3") == StorageDriver.S3
        assert StorageDriver("memory") == StorageDriver.MEMORY

    def test_storage_driver_is_strenum(self) -> None:
        """Test StorageDriver is a StrEnum."""
        assert isinstance(StorageDriver.LOCAL, str)
        assert StorageDriver.LOCAL == "local"


class TestAdminFileInfo:
    """Tests for AdminFileInfo dataclass."""

    def test_admin_file_info_creation(self) -> None:
        """Test creating AdminFileInfo."""
        now = datetime.now(timezone.utc)
        info = AdminFileInfo(
            path="/uploads/test.txt",
            size=1024,
            content_type="text/plain",
            last_modified=now,
        )
        assert info.path == "/uploads/test.txt"
        assert info.size == 1024
        assert info.content_type == "text/plain"
        assert info.last_modified == now
        assert info.etag is None
        assert info.metadata is None

    def test_admin_file_info_with_optional(self) -> None:
        """Test AdminFileInfo with optional fields."""
        now = datetime.now(timezone.utc)
        info = AdminFileInfo(
            path="/uploads/test.txt",
            size=1024,
            content_type="text/plain",
            last_modified=now,
            etag="abc123",
            metadata={"author": "test"},
            uploaded_by="user-1",
            resource_type="avatar",
            resource_id="user-1",
        )
        assert info.etag == "abc123"
        assert info.metadata == {"author": "test"}
        assert info.uploaded_by == "user-1"
        assert info.resource_type == "avatar"
        assert info.resource_id == "user-1"


class TestUploadResult:
    """Tests for UploadResult dataclass."""

    def test_upload_result_with_file_info(self) -> None:
        """Test UploadResult carrying file info and a public URL."""
        now = datetime.now(timezone.utc)
        file_info = AdminFileInfo(
            path="/uploads/test.txt",
            size=1024,
            content_type="text/plain",
            last_modified=now,
        )
        result = UploadResult(
            file_info=file_info,
            url="https://example.com/test.txt",
        )
        assert result.file_info is not None
        assert result.url == "https://example.com/test.txt"

    def test_upload_result_defaults(self) -> None:
        """Test UploadResult with no optional fields populated."""
        result = UploadResult()
        assert result.file_info is None
        assert result.url is None


class TestAdminUploadOptions:
    """Tests for AdminUploadOptions dataclass."""

    def test_admin_upload_options_defaults(self) -> None:
        """Test AdminUploadOptions default values."""
        options = AdminUploadOptions()
        assert options.content_type is None
        assert options.metadata is None
        assert options.public is False
        assert options.resource_type is None
        assert options.resource_id is None
        assert options.allowed_types is None
        assert options.max_size is None

    def test_admin_upload_options_with_values(self) -> None:
        """Test AdminUploadOptions with values."""
        options = AdminUploadOptions(
            content_type="image/png",
            metadata={"cache-control": "max-age=3600"},
            public=True,
            resource_type="avatar",
            resource_id="user-1",
            allowed_types=["png", "jpg", "gif"],
            max_size=5_000_000,
        )
        assert options.content_type == "image/png"
        assert options.metadata == {"cache-control": "max-age=3600"}
        assert options.public is True
        assert options.resource_type == "avatar"
        assert options.resource_id == "user-1"
        assert options.allowed_types == ["png", "jpg", "gif"]
        assert options.max_size == 5_000_000

    def test_admin_upload_options_to_storage_options(self) -> None:
        """Test converting AdminUploadOptions to UploadOptions."""
        options = AdminUploadOptions(
            content_type="image/png",
            metadata={"cache-control": "max-age=3600"},
            public=True,
        )
        storage_options = options.to_storage_options()
        assert storage_options.content_type == "image/png"
        assert storage_options.metadata == {"cache-control": "max-age=3600"}
        assert storage_options.public is True
