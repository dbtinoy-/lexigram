---
title: lexigram-storage How-Tos
description: Task-oriented recipes for common blob and KV storage operations.
---

## Wire Storage in Your App

```python
from lexigram import Application
from lexigram.storage import StorageModule, StorageConfig

app = Application(name="myapp")
app.add_module(
    StorageModule.configure(
        StorageConfig(default_driver="local")
    )
)
await app.start()
```

## Upload and Download Files

```python
from lexigram.contracts import BlobStoreProtocol, FileInfo


class FileService:
    def __init__(self, store: BlobStoreProtocol) -> None:
        self.store = store

    async def upload(self, path: str, data: bytes) -> FileInfo:
        return await self.store.upload(path, data)

    async def download(self, path: str) -> bytes:
        return await self.store.download(path)

    async def stream(self, path: str, chunk_size: int = 8192):
        async for chunk in self.store.stream(path, chunk_size=chunk_size):
            yield chunk

    async def delete(self, path: str) -> None:
        await self.store.delete(path)

    async def exists(self, path: str) -> bool:
        return await self.store.exists(path)

    async def get_file_info(self, path: str) -> FileInfo:
        return await self.store.info(path)
```

## List Files with a Prefix

```python
async def list_avatars(
    store: BlobStoreProtocol,
) -> list[FileInfo]:
    avatars = []
    async for info in store.list(prefix="avatars/"):
        avatars.append(info)
    return avatars
```

## Generate Presigned URLs

```python
from datetime import timedelta


class ShareService:
    def __init__(self, store: BlobStoreProtocol) -> None:
        self.store = store

    async def create_share_link(
        self, path: str, expires_in_hours: int = 24,
    ) -> str:
        return await self.store.get_presigned_url(
            path,
            expires_in=timedelta(hours=expires_in_hours),
            method="GET",
        )

    async def create_upload_url(
        self, path: str,
    ) -> str:
        """Generate a temporary upload URL for direct client uploads."""
        return await self.store.get_presigned_url(
            path,
            expires_in=timedelta(minutes=15),
            method="PUT",
        )
```

## Configure S3 with MinIO for Local Development

```yaml
storage:
  default_driver: s3
  drivers:
    s3:
      bucket: myapp-dev
      region: us-east-1
      endpoint_url: http://localhost:9000
      access_key: minioadmin
      secret_key: minioadmin
```

```bash
docker run -p 9000:9000 -p 9001:9001 minio/minio server /data
```

## Use the In-Memory Driver for Tests

```python
from lexigram.storage import StorageModule, StorageConfig


# Fast, isolated tests with no I/O
app = Application(name="test", testing=True)
app.add_module(
    StorageModule.stub()  # uses memory driver
)
await app.start()
```

## Copy and Move Files

```python
# Using StorageDriverProtocol (available via DriverRegistry)
from lexigram.contracts.infra.storage import StorageDriverProtocol


class MediaManager:
    def __init__(self, store: BlobStoreProtocol) -> None:
        self.store = store

    async def archive(self, source: str, dest: str) -> None:
        if isinstance(self.store, StorageDriverProtocol):
            await self.store.copy(source, dest)
            await self.store.delete(source)
        else:
            data = await self.store.download(source)
            await self.store.upload(dest, data)
            await self.store.delete(source)
```

## Use KV Storage for Caching

```python
from lexigram.storage.kv import InMemoryKVStorage


class SimpleCache:
    def __init__(self) -> None:
        self._store = InMemoryKVStorage()

    async def get(self, key: str) -> dict | None:
        return await self._store.get(key)

    async def set(
        self, key: str, value: dict, ttl: int = 300,
    ) -> None:
        await self._store.set(key, value, ttl=ttl)

    async def delete(self, key: str) -> None:
        await self._store.delete(key)

    async def has(self, key: str) -> bool:
        return await self._store.exists(key)
```
