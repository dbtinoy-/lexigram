---
title: lexigram-storage Guide
description: Mental model, core concepts, and common patterns for blob and KV storage.
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `boto3` | Recommended | S3 / R2 storage backend |
| `google-cloud-storage` | Optional | GCS storage backend |
| `azure-storage-blob` | Optional | Azure Blob storage backend |

## Problem

Your application needs to store and retrieve files — user avatars, PDF reports, data exports — across one or more cloud providers. You want a single API that works with S3, GCS, Azure Blob, Cloudflare R2, and local filesystem, and you want to switch between them without rewriting code.

## Mental Model

`lexigram-storage` exposes **two storage paradigms**:

### Blob / Object Storage (Primary API)

For arbitrary binary objects — files, images, documents, backups. Operations include upload, download, delete, list, generate presigned URLs, and streaming.

**Protocol:** `BlobStoreProtocol` from `lexigram-contracts`.

### Key-Value (KV) Storage

For small, string-keyed records — session data, feature flags, ephemeral state — with optional TTL. KV is JSON-based and does **not** support binary blobs or presigned URLs.

**Classes:** `InMemoryKVStorage`, `LocalStorage` in `lexigram.storage.kv`.

---

## Core Concepts

### BlobStoreProtocol

The primary interface for file storage. Every backend driver implements it.

```python
from lexigram.contracts import BlobStoreProtocol


class AvatarService:
    def __init__(self, store: BlobStoreProtocol) -> None:
        self.store = store

    async def upload_avatar(self, user_id: str, data: bytes) -> str:
        info = await self.store.upload(
            f"avatars/{user_id}.jpg",
            data,
            content_type="image/jpeg",
        )
        return info.path

    async def get_avatar_url(self, user_id: str) -> str:
        return await self.store.get_presigned_url(
            f"avatars/{user_id}.jpg",
            expires_in=timedelta(hours=1),
        )
```

### Drivers (Backends)

| Driver | Identifier | Extras Required | Use Case |
|--------|-----------|----------------|----------|
| **Local** | `"local"` | None | Dev, single-node deployments |
| **Memory** | `"memory"` | None | Unit tests |
| **S3** | `"s3"` | `[aws]` | AWS production |
| **GCS** | `"gcs"` | `[gcp]` | GCP production |
| **Azure** | `"azure"` | `[azure]` | Azure production |
| **R2** | `"r2"` | `[aws]` | Cloudflare R2 |

### DriverRegistry

The `DriverRegistry` maps driver names to implementations and creates driver instances from config. It is extensible — third-party packages can register new drivers via the `lexigram.storage.backends` entry-point group.

### Multi-Backend

Declare multiple stores with named bindings:

```yaml
storage:
  backends:
    - name: avatars
      driver: s3
      s3:
        bucket: myapp-avatars
        region: us-east-1
    - name: exports
      driver: s3
      s3:
        bucket: myapp-exports
        region: us-east-1
```

Resolve with `Annotated[BlobStoreProtocol, Named("name")]`.

### Upload Options

Fine-grained control over uploaded files:

```python
from lexigram.storage import UploadOptions

options = UploadOptions(
    content_type="application/pdf",
    public=True,
    metadata={"department": "finance"},
    cache_control="public, max-age=3600",
)
info = await store.upload(path, data, **options.__dict__)
```

---

## Typical Usage

### File Upload and Download

```python
class DocumentService:
    def __init__(self, store: BlobStoreProtocol) -> None:
        self.store = store

    async def save_document(
        self, doc_id: str, content: bytes, mime: str,
    ) -> FileInfo:
        return await self.store.upload(
            f"docs/{doc_id}.pdf",
            content,
            content_type=mime,
        )

    async def get_document(self, doc_id: str) -> bytes:
        return await self.store.download(f"docs/{doc_id}.pdf")

    async def stream_document(self, doc_id: str):
        async for chunk in self.store.stream(f"docs/{doc_id}.pdf"):
            yield chunk

    async def list_documents(self) -> AsyncIterator[FileInfo]:
        return self.store.list(prefix="docs/")
```

### Presigned URLs

```python
# Generate a temporary download URL
url = await store.get_presigned_url(
    "reports/monthly.pdf",
    expires_in=timedelta(hours=24),
    method="GET",
)

# Generate a temporary upload URL
upload_url = await store.get_presigned_url(
    "uploads/temp.bin",
    expires_in=timedelta(minutes=15),
    method="PUT",
)
```

---

## Common Patterns

### Multi-Backend with Named Stores

```python
from typing import Annotated
from lexigram.di.markers import Named


class MediaService:
    def __init__(
        self,
        primary: BlobStoreProtocol,
        thumbnails: Annotated[BlobStoreProtocol, Named("thumbnails")],
    ) -> None:
        self.primary = primary
        self.thumbnails = thumbnails
```

### KV Storage for Session Data

```python
from lexigram.storage.kv import InMemoryKVStorage


class SessionStore:
    def __init__(self) -> None:
        self._kv = InMemoryKVStorage()

    async def set(self, key: str, value: dict, ttl: int = 3600) -> None:
        await self._kv.set(key, value, ttl=ttl)

    async def get(self, key: str) -> dict | None:
        return await self._kv.get(key)
```

### Server-Side Encryption

```python
from lexigram.storage.config import StorageS3Config, EncryptionConfig

config = StorageS3Config(
    bucket="myapp-secure",
    region="us-east-1",
    encryption=EncryptionConfig(enabled=True, type="AES256"),
)
```

---

## Best Practices

- ✅ Use the memory driver in unit tests — it's fast and stateless.
- ✅ Use the local driver in development with a `.gitkeep` in the root dir.
- ✅ Set `storage.default_driver` to the production backend and override via `LEX_STORAGE__DEFAULT_DRIVER` in each environment.
- ❌ Don't store secrets (passwords, API keys) in KV — use `lexigram-auth` or a vault.
- ❌ Don't use the local driver in production across multiple app instances — files won't be shared.
- ❌ Don't use presigned URLs with `method="PUT"` for untrusted uploads without additional validation.

## Next Steps

- [How-Tos](./HOWTOS.md) — task-oriented recipes
- [Architecture](./ARCHITECTURE.md) — internal design and extension points
- [Configuration](./CONFIGURATION.md) — every config key
