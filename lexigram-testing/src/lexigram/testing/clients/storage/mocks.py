"""Mock storage implementations for testing"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

from lexigram.contracts.infra.storage import BlobStoreProtocol, FileInfo


class MockStorage(BlobStoreProtocol):
    """Mock storage implementation for testing"""

    def __init__(self) -> None:
        self.upload: Any = AsyncMock()
        self.download: Any = AsyncMock()
        self.stream: Any = AsyncMock()
        self.delete: Any = AsyncMock()
        self.exists: Any = AsyncMock(return_value=True)
        self.info: Any = AsyncMock()
        self.list: Any = AsyncMock()
        self.get_url: Any = AsyncMock(return_value="http://mock-url")
        self.get_presigned_url: Any = AsyncMock(
            return_value="http://mock-presigned-url",
        )

    def configure_upload_response(self, file_info: FileInfo) -> None:
        """Configure the upload method to return specific file info"""
        self.upload.return_value = file_info

    def configure_download_response(self, content: bytes) -> None:
        """Configure the download method to return specific content"""
        self.download.return_value = content

    def configure_info_response(self, file_info: FileInfo) -> None:
        """Configure the info method to return specific file info"""
        self.info.return_value = file_info

    def configure_exists_response(self, exists: bool = True) -> None:
        """Configure the exists method response"""
        self.exists.return_value = exists
