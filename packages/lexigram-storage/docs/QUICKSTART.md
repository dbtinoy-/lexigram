---
title: lexigram-storage Quickstart
description: Get up and running with unified blob storage in minutes.
---

:::tip[Package]
`lexigram-storage` — Unified blob storage abstraction for S3, GCS, Azure Blob, Cloudflare R2, and local filesystem.
:::

## Install

```bash
uv add lexigram-storage
```

Add optional extras for cloud backends:

```bash
uv add "lexigram-storage[aws]"    # aiobotocore for S3, R2
uv add "lexigram-storage[gcp]"    # gcloud-aio-storage for GCS
uv add "lexigram-storage[azure]"  # azure-storage-blob for Azure
```

The local and memory drivers require no extra dependencies.

---

## Minimal Example

```python
import asyncio
from lexigram import Application
from lexigram.contracts import BlobStoreProtocol
from lexigram.storage import StorageModule, StorageConfig


async def main() -> None:
    async with Application.boot(
        name="storage-demo",
        modules=[
            StorageModule.configure(
                StorageConfig(default_driver="memory")
            ),
        ],
    ) as app:
        store = await app.container.resolve(BlobStoreProtocol)
        info = await store.upload("hello.txt", b"Hello, world!")
        print(f"Uploaded: {info.path} ({info.size} bytes)")
        data = await store.download("hello.txt")
        print(f"Downloaded: {data.decode()}")


asyncio.run(main())
```

For local filesystem:

```python
config = StorageConfig(
    default_driver="local",
    drivers={"local": {"root_dir": "./storage"}},
)
```

---

## What Just Happened

1. **`StorageModule.configure()`** creates a `StorageProvider` with the given config.
2. The provider registers a `BlobStoreProtocol` singleton in the container.
3. On boot, it verifies connectivity (health check).
4. Your service receives the store via constructor injection.

## Next Steps

- [Guide](./GUIDE.md) — mental model, core concepts, common patterns
- [How-Tos](./HOWTOS.md) — task-oriented recipes
- [Configuration](./CONFIGURATION.md) — every config key with env-var names
