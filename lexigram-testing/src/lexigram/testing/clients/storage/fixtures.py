"""Pytest fixtures for storage testing"""

from __future__ import annotations

# Import formatting handled intentionally for the pytest compatibility try/except
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from types import ModuleType

    pytest_asyncio: ModuleType | None

try:
    import pytest_asyncio
except ImportError:
    pytest_asyncio = None

from lexigram.contracts.infra.storage import BlobStoreProtocol
from lexigram.storage.backends import MemoryDriver
from lexigram.testing import TestEnvironment


@pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture
async def storage_test_bed() -> Any:
    """Test bed with storage services"""
    test_bed = TestEnvironment()

    # Add memory storage driver
    storage_driver = MemoryDriver()
    assert test_bed.container is not None
    test_bed.container.singleton(BlobStoreProtocol, storage_driver)

    async with test_bed:  # type: ignore[attr-defined]
        yield test_bed


@pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture
async def storage_test_client(storage_test_bed: Any) -> Any:
    """Test client for storage operations"""
    assert storage_test_bed.container is not None
    return StorageTestClient(
        await storage_test_bed.container.resolve(BlobStoreProtocol)
    )


class StorageTestClient:
    """Test client for storage operations"""

    def __init__(self, storage: BlobStoreProtocol):
        self.storage = storage

    async def upload_test_file(self, path: str, content: str = "test content") -> None:
        """Upload a test file"""
        await self.storage.upload(path, content.encode("utf-8"))

    async def download_test_file(self, path: str) -> str:
        """Download a test file"""
        data = await self.storage.download(path)
        return data.decode("utf-8")

    async def cleanup_test_files(self, *paths: str) -> None:
        """Clean up test files"""
        for path in paths:
            try:
                await self.storage.delete(path)
            except Exception as e:  # noqa: BLE001
                from lexigram.logging import get_logger

                get_logger(__name__).debug(
                    "Storage fixture cleanup ignored missing file or error: %s",
                    e,
                )  # Ignore if file doesn't exist or deletion fails
