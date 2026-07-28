"""Unit tests for storage testing utilities"""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from lexigram.testing.clients.storage.fixtures import StorageTestClient
from lexigram.testing.clients.storage.mocks import MockStorage
from lexigram.contracts.infra.storage import FileInfo


class TestMockStorage:
    """Test the MockStorage class"""

    def test_mock_storage_initialization(self):
        """Test MockStorage initializes with mocked methods"""
        mock = MockStorage()

        # Check that all methods are AsyncMock instances
        assert isinstance(mock.upload, AsyncMock)
        assert isinstance(mock.download, AsyncMock)
        assert isinstance(mock.stream, AsyncMock)
        assert isinstance(mock.delete, AsyncMock)
        assert isinstance(mock.exists, AsyncMock)
        assert isinstance(mock.info, AsyncMock)
        assert isinstance(mock.list, AsyncMock)
        assert isinstance(mock.get_url, AsyncMock)
        assert isinstance(mock.get_presigned_url, AsyncMock)

    def test_mock_storage_default_exists(self):
        """Test exists method defaults to True"""
        mock = MockStorage()
        assert mock.exists.return_value is True

    def test_mock_storage_default_urls(self):
        """Test URL methods have default return values"""
        mock = MockStorage()
        assert mock.get_url.return_value == "http://mock-url"
        assert mock.get_presigned_url.return_value == "http://mock-presigned-url"

    def test_configure_upload_response(self):
        """Test configuring upload response"""
        mock = MockStorage()
        file_info = FileInfo(
            path="test.txt",
            size=100,
            content_type="text/plain",
            last_modified=datetime.now(),
        )

        mock.configure_upload_response(file_info)
        assert mock.upload.return_value == file_info

    def test_configure_download_response(self):
        """Test configuring download response"""
        mock = MockStorage()
        content = b"test content"

        mock.configure_download_response(content)
        assert mock.download.return_value == content

    def test_configure_info_response(self):
        """Test configuring info response"""
        mock = MockStorage()
        file_info = FileInfo(
            path="test.txt",
            size=100,
            content_type="text/plain",
            last_modified=datetime.now(),
        )

        mock.configure_info_response(file_info)
        assert mock.info.return_value == file_info

    def test_configure_exists_response(self):
        """Test configuring exists response"""
        mock = MockStorage()

        mock.configure_exists_response(False)
        assert mock.exists.return_value is False

        mock.configure_exists_response(True)
        assert mock.exists.return_value is True


class TestStorageTestClient:
    """Test the StorageTestClient class"""

    @pytest.fixture
    def mock_storage(self):
        """Create a mock storage for testing"""
        return MockStorage()

    @pytest.fixture
    def test_client(self, mock_storage):
        """Create a test client with mock storage"""
        return StorageTestClient(mock_storage)

    @pytest.mark.asyncio
    async def test_upload_test_file_default_content(self, test_client, mock_storage):
        """Test uploading a test file with default content"""
        await test_client.upload_test_file("test.txt")

        mock_storage.upload.assert_called_once_with("test.txt", b"test content")

    @pytest.mark.asyncio
    async def test_upload_test_file_custom_content(self, test_client, mock_storage):
        """Test uploading a test file with custom content"""
        custom_content = "custom test content"
        await test_client.upload_test_file("test.txt", custom_content)

        mock_storage.upload.assert_called_once_with(
            "test.txt", custom_content.encode("utf-8"),
        )

    @pytest.mark.asyncio
    async def test_download_test_file(self, test_client, mock_storage):
        """Test downloading a test file"""
        mock_storage.download.return_value = b"downloaded content"

        result = await test_client.download_test_file("test.txt")

        assert result == "downloaded content"
        mock_storage.download.assert_called_once_with("test.txt")

    @pytest.mark.asyncio
    async def test_cleanup_test_files(self, test_client, mock_storage):
        """Test cleaning up test files"""
        await test_client.cleanup_test_files("file1.txt", "file2.txt")

        assert mock_storage.delete.call_count == 2
        mock_storage.delete.assert_any_call("file1.txt")
        mock_storage.delete.assert_any_call("file2.txt")

    @pytest.mark.asyncio
    async def test_cleanup_test_files_with_errors(self, test_client, mock_storage):
        """Test cleanup handles deletion errors gracefully"""
        mock_storage.delete.side_effect = Exception("Delete failed")

        # Should not raise an exception
        await test_client.cleanup_test_files("file1.txt")

        mock_storage.delete.assert_called_once_with("file1.txt")
