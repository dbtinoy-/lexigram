---
title: "File Storage"
description: "Object and blob storage with a single protocol — swap S3, GCS, Azure Blob, R2, or local filesystem via config."
---

`lexigram-storage` puts one protocol in front of every major object store. Application code depends on `BlobStoreProtocol`; the driver (`local`, `s3`, `gcs`, `azure`, `r2`, or `memory`) is chosen in configuration. Dev runs on disk, production on S3 or GCS, tests on the in-memory driver — none of which requires changes to the services that read and write files. Presigned URLs are part of the protocol, so you can hand out time-limited links without coupling to a provider SDK.

For the full configuration reference, see the [`lexigram-storage` package docs](/packages/lexigram-storage/).

---

## 1. The Contract

All drivers implement `BlobStoreProtocol`. Operations return raw bytes, a `FileInfo` record, or a URL string; infrastructure failures raise:

```python
from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Any, Protocol, runtime_checkable
from lexigram.contracts.infra.storage import FileInfo


@runtime_checkable
class BlobStoreProtocol(Protocol):
    async def upload(self, path: str, data: bytes | AsyncIterator[bytes],
                     content_type: str | None = None, **options: Any) -> FileInfo: ...
    async def download(self, path: str) -> bytes: ...
    def stream(self, path: str, chunk_size: int = 8192) -> AsyncIterator[bytes]: ...
    async def delete(self, path: str) -> None: ...
    async def exists(self, path: str) -> bool: ...
    async def info(self, path: str) -> FileInfo: ...
    def list(self, prefix: str = "") -> AsyncIterator[FileInfo]: ...
    async def get_url(self, path: str) -> str: ...
    async def get_presigned_url(self, path: str,
                                expires_in: timedelta = timedelta(hours=1),
                                method: str = "GET") -> str: ...
```

`FileInfo` is a frozen dataclass with `path`, `size`, `content_type`, `last_modified`, plus optional `etag` and `metadata`.

---

## 2. Configuration

Add the provider and configure the `storage` section. Pick a driver with `default_driver` and place its settings under `drivers.<name>`. The `local` driver needs no external service:

```python
from lexigram import Application
from lexigram.storage import StorageProvider

app = Application(name="my-app")
app.add_provider(StorageProvider())
```

```yaml title="application.yaml" {dev}
storage:
  default_driver: "local"
  drivers:
    local:
      root_dir: "./data/uploads"
      base_url: "http://localhost:8000/files"
```

For production, switch to `s3` — credentials come from environment variables so they stay out of the config file:

```yaml title="application.yaml" {prod}
storage:
  default_driver: "s3"
  drivers:
    s3:
      bucket: "my-app-uploads"
      region: "us-east-1"
      access_key: "${AWS_ACCESS_KEY_ID}"
      secret_key: "${AWS_SECRET_ACCESS_KEY}"
      endpoint_url: null         # set for MinIO, LocalStack
      encryption:
        enabled: true
        type: "AES256"           # or "aws:kms" with kms_key_id
  service:
    max_file_size_mb: 100
```

GCS, Azure, and Cloudflare R2 follow the same shape; see the package docs for driver-specific fields.

---

## 3. Uploading

Inject `BlobStoreProtocol` into any service. Pass bytes (or an async iterator for large payloads) with the MIME type. The returned `FileInfo` carries the metadata the backend recorded:

```python
from lexigram.contracts.infra.storage import BlobStoreProtocol, FileInfo


class AvatarService:
    def __init__(self, storage: BlobStoreProtocol) -> None:
        self._storage = storage

    async def save_avatar(self, user_id: str, image: bytes) -> FileInfo:
        return await self._storage.upload(
            path=f"avatars/{user_id}.png",
            data=image,
            content_type="image/png",
            metadata={"user_id": user_id, "uploaded_by": "self"},
        )
```

`path` is the object key — `avatars/...` prefixes are convention, not nesting; cloud backends treat the whole string as a flat key.

---

## 4. Reading, Listing, and Deleting

`download` pulls the full object into memory — fine for small files. For larger payloads, `stream` yields chunks without buffering the body. `list(prefix)` is an async iterator of `FileInfo`; `delete(path)` removes a single key; `exists(path)` is the cheap probe before a download. `info(path)` returns metadata without transferring the body:

```python
class FileService:
    def __init__(self, storage: BlobStoreProtocol) -> None:
        self._storage = storage

    async def read_small(self, path: str) -> bytes:
        return await self._storage.download(path)

    async def write_to_disk(self, path: str, target: str) -> None:
        with open(target, "wb") as out:
            async for chunk in self._storage.stream(path, chunk_size=64 * 1024):
                out.write(chunk)

    async def purge_user_files(self, user_id: str) -> int:
        deleted = 0
        async for item in self._storage.list(f"users/{user_id}/"):
            await self._storage.delete(item.path)
            deleted += 1
        return deleted
```

---

## 5. Presigned URLs

Hand out time-limited URLs so clients download (or upload) directly without proxying bytes through your service. `expires_in` is a `timedelta`; pass `method="PUT"` for browser-driven uploads:

```python
from datetime import timedelta


class ShareService:
    def __init__(self, storage: BlobStoreProtocol) -> None:
        self._storage = storage

    async def share_link(self, path: str) -> str:
        return await self._storage.get_presigned_url(path, expires_in=timedelta(minutes=15))

    async def issue_upload_slot(self, path: str) -> str:
        return await self._storage.get_presigned_url(path, expires_in=timedelta(minutes=5), method="PUT")
```

:::note
Presigned URLs are bearer credentials for the duration of `expires_in`. Keep the window short (minutes, not days) and never log the full URL. Cloud backends also require the signing IAM principal to retain the underlying permission for the URL to keep working.
:::

The `local` driver returns a deterministic URL built from `base_url` rather than signing — it stands in for the protocol shape during development, not as a security boundary.

---

## 6. Multiple Backends

Declare a `backends` list to register several stores side-by-side. Each entry has a `name`, a `driver`, and per-driver settings nested under the driver name. Mark one entry `primary: true` — it also receives the unnamed binding:

```yaml title="application.yaml"
storage:
  backends:
    - name: uploads
      driver: s3
      primary: true
      s3: { bucket: "my-app-uploads", region: "us-east-1" }
    - name: avatars
      driver: s3
      s3: { bucket: "my-app-avatars", region: "us-east-1" }
```

Inject named backends with `Named`:

```python
from typing import Annotated
from lexigram.contracts.infra.storage import BlobStoreProtocol
from lexigram.di.markers import Named


class MediaService:
    def __init__(
        self,
        uploads: BlobStoreProtocol,                                  # primary
        avatars: Annotated[BlobStoreProtocol, Named("avatars")],
    ) -> None:
        self._uploads = uploads
        self._avatars = avatars
```

---

## 7. Testing

For unit tests, `StorageModule.stub()` registers an in-memory backend that satisfies `BlobStoreProtocol` with no filesystem or network:

```python
from lexigram import Application
from lexigram.storage import StorageModule
from lexigram.contracts.infra.storage import BlobStoreProtocol


async def test_avatar_round_trip() -> None:
    async with Application.boot(modules=[StorageModule.stub()]) as app:
        storage = await app.container.resolve(BlobStoreProtocol)
        await storage.upload("u1.png", b"\x89PNG...", content_type="image/png")
        assert (await storage.download("u1.png")).startswith(b"\x89PNG")
```

For tests that exercise the real filesystem layout, point the `local` driver at a `tmp_path` fixture instead — same protocol, real disk semantics.

---

## Next Steps

- [Multi-tenancy](/guides/multi-tenancy/) — tenant-scoped buckets and key prefixes
- [Dependency Injection](/fundamentals/dependency-injection/) — binding `BlobStoreProtocol` to a driver
- [`lexigram-storage` package](/packages/lexigram-storage/) — driver-specific options, encryption, KV store
