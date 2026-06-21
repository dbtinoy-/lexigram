"""Tests for admin storage presigned-URL fallback to public URLs."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from lexigram.admin.services.storage.service import AdminStorageService
from lexigram.admin.services.storage.upload import FileUploadService
from lexigram.storage.exceptions import StorageUnsupportedOperationError


class UnsupportedPresignStore:
    """Store stub that rejects presigned URLs but serves public URLs."""

    def __init__(self) -> None:
        self.presigned_calls: list[tuple[str, str]] = []

    async def get_presigned_url(self, path: str, expires_in=None, method: str = "GET") -> str:
        self.presigned_calls.append((path, method))
        raise StorageUnsupportedOperationError("unsupported")

    async def get_url(self, path: str) -> str:
        return f"https://public.example/{path.lstrip('/')}"


@pytest.fixture
def store() -> UnsupportedPresignStore:
    return UnsupportedPresignStore()


@pytest.fixture
def service(store: UnsupportedPresignStore) -> AdminStorageService:
    config = SimpleNamespace(presigned_url_expiry=3600, base_path="uploads")
    return AdminStorageService(blob_store=store, config=config)  # type: ignore[arg-type]


class TestGetDownloadUrlFallsBack:
    @pytest.mark.asyncio
    async def test_local_style_store_returns_public_url(
        self, service: AdminStorageService, store: UnsupportedPresignStore
    ) -> None:
        url = await service.get_download_url("uploads/a.txt")
        assert url == "https://public.example/uploads/a.txt"
        assert store.presigned_calls == [("uploads/a.txt", "GET")]

    @pytest.mark.asyncio
    async def test_uses_configured_expiry(self, service: AdminStorageService) -> None:
        url = await service.get_download_url("uploads/a.txt", expires_in=7200)
        assert url == "https://public.example/uploads/a.txt"


class TestGetUploadUrlFallsBack:
    @pytest.mark.asyncio
    async def test_local_style_store_returns_public_url_with_path(
        self, service: AdminStorageService, store: UnsupportedPresignStore
    ) -> None:
        url, path = await service.get_upload_url(
            "report.pdf", resource_type="invoices", resource_id=7
        )
        assert url == f"https://public.example/{path.lstrip('/')}"
        assert path.startswith("uploads/")
        assert store.presigned_calls[-1][1] == "PUT"


class TestFileUploadServiceFallsBack:
    @pytest.mark.asyncio
    async def test_private_upload_returns_public_url(self) -> None:
        from unittest.mock import AsyncMock

        from lexigram.contracts.infra.storage import UploadOptions

        storage = UnsupportedPresignStore()
        storage.upload = AsyncMock(  # type: ignore[attr-defined]
            return_value=SimpleNamespace(path="uploads/abc.txt")
        )
        svc = FileUploadService(storage=storage)  # type: ignore[arg-type]
        uploaded, err = await svc.upload(
            Mock(read=Mock(return_value=b"data")), "a.txt", content_type="text/plain"
        )
        assert err == ""
        assert uploaded is not None
        storage_path = uploaded.storage_path
        assert storage_path.startswith("admin/")
        assert uploaded.url == f"https://public.example/{storage_path}"
        assert storage.presigned_calls == [(storage_path, "GET")]
        storage.upload.assert_awaited_once()  # type: ignore[attr-defined]
        kwargs = storage.upload.await_args.kwargs  # type: ignore[attr-defined]
        assert "options" in kwargs
        assert isinstance(kwargs["options"], UploadOptions)
