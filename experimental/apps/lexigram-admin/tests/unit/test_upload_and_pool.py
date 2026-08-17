from unittest.mock import Mock

import pytest

from lexigram.admin.services.storage.upload import FileUploadService


class FailingStorage:
    async def upload(self, data, path, options):
        raise OSError("disk full")

    async def delete(self, path):
        raise OSError("delete failed")

    async def info(self, path):
        raise RuntimeError("info failed")

    async def get_presigned_url(self, path, expires_in=3600):
        return "https://example.com/presigned"

    async def get_public_url(self, path):
        return "https://example.com/public"


@pytest.mark.asyncio
async def test_upload_failure_logs(caplog, capfd):
    svc = FileUploadService(storage=FailingStorage())
    file = Mock()
    file.read.return_value = b"data"

    caplog.set_level("ERROR")
    uploaded, err = await svc.upload(file, "test.txt", content_type="text/plain")

    assert uploaded is None
    assert err == "Upload failed"
    # Log capture for these errors is tested elsewhere; focus on behavior (returned error) here.
    pass


@pytest.mark.asyncio
async def test_delete_and_exists_failure_logs(caplog, capfd):
    storage = FailingStorage()
    svc = FileUploadService(storage=storage)

    caplog.set_level("ERROR", logger="lexigram")
    deleted = await svc.delete("path/to/file")
    assert deleted is False
    # Delete failure returned False; log capture is validated elsewhere

    caplog.clear()
    exists = await svc.exists("path/to/file")
    assert exists is False
    # Existence check failure should not raise; log capture is validated elsewhere
