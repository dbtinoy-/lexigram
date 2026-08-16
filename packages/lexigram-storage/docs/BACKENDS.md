---
title: lexigram-storage Backends
description: Supported storage backends in lexigram-storage — S3, GCS, Azure Blob, R2, local filesystem, and in-memory
---

`lexigram-storage` provides blob storage through a unified `BlobStoreProtocol` interface. Each driver implements upload, download, delete, list, URL generation, and health-checking. The package also provides a separate key-value storage subsystem (`lexigram.storage.kv`) for small string-keyed records with TTL.

## Supported Backends

| Backend | Extra / Package | Production Ready | Best For |
|---------|----------------|-----------------|----------|
| **AWS S3** | `[aws]` | Yes | General-purpose cloud object storage |
| **Google Cloud Storage** | `[gcp]` | Yes | GCP-native blob storage |
| **Azure Blob Storage** | `[azure]` | Yes | Azure-native blob storage |
| **Cloudflare R2** | `[aws]` | Yes | S3-compatible, zero egress fees |
| **Local Filesystem** | *(none)* | Dev/Test | Local development, CI |
| **Memory** | *(none)* | No | Unit tests, prototyping |

### AWS S3

Industry-standard object storage with configurable endpoint (for MinIO, DigitalOcean Spaces, etc.), server-side encryption, and public URL overrides. Supports SSE-S3 and SSE-KMS encryption types.

```yaml
storage:
  default_driver: s3
  drivers:
    s3:
      bucket: my-app-files
      region: us-east-1
      access_key: "${AWS_ACCESS_KEY_ID}"
      secret_key: "${AWS_SECRET_ACCESS_KEY}"
      encryption:
        enabled: true
        type: AES256
```

```python
from lexigram.storage import StorageProvider, StorageConfig

provider = StorageProvider(config=StorageConfig(
    default_driver="s3",
    drivers={"s3": StorageS3Config(bucket="my-app-files", region="us-east-1")},
))
```

### Google Cloud Storage

GCS object storage with workload identity or service account credentials. Supports CMEK encryption for customer-managed keys.

```yaml
storage:
  default_driver: gcs
  drivers:
    gcs:
      bucket: my-app-assets
      project_id: my-gcp-project
      credentials_path: /etc/gcp/service-account.json
```

### Azure Blob Storage

Azure's blob service with account name/key authentication and container-level organisation.

```yaml
storage:
  default_driver: azure
  drivers:
    azure:
      account_name: myappstorage
      account_key: "${AZURE_STORAGE_KEY}"
      container: files
```

### Cloudflare R2

S3-compatible object storage with zero egress fees. Uses the S3 driver under the hood (`aiobotocore`) but requires explicit `access_key`, `secret_key`, and `endpoint_url` — IAM roles are not supported.

```yaml
storage:
  default_driver: r2
  drivers:
    r2:
      bucket: my-app-assets
      access_key: "${R2_ACCESS_KEY_ID}"
      secret_key: "${R2_SECRET_ACCESS_KEY}"
      endpoint_url: https://<account>.r2.cloudflarestorage.com
      public_url: https://cdn.example.com
```

### Local Filesystem

An `aiofiles`-backed driver that stores blobs as regular files under a configurable root directory. Supports `base_url` for serving files through a local web server.

```yaml
storage:
  default_driver: local
  drivers:
    local:
      root_dir: ./storage/data
      base_url: /files
```

### Memory

Ephemeral dictionary-backed driver. All data is lost on process restart. Zero configuration required.

```yaml
storage:
  default_driver: memory
  drivers:
    memory: {}
```

## Blob Store vs. Key-Value Paradigm

`lexigram-storage` exposes two distinct storage paradigms in one package:

**Blob / Object Storage** — the primary API. Arbitrary binary objects (files, images, documents) with upload, download, signed URLs, and streaming. All six drivers above implement `BlobStoreProtocol`.

**Key-Value (KV) Storage** — `lexigram.storage.kv` for small string-keyed JSON records with optional TTL. Two backends:
- `InMemoryKVStorage` — ephemeral dict-backed store (unit tests, single-node apps)
- `LocalStorage` — JSON-file-backed persistent store (dev environments)

```python
from lexigram.storage.kv import InMemoryKVStorage

store = InMemoryKVStorage()
await store.set("session:abc", {"user": "42"}, ttl=3600)
value = await store.get("session:abc")
```

Use blob storage for files and cloud-hosted durable storage. Use KV storage for session data, feature flags, and ephemeral state.

## Quick Selection Guide

| If you need… | Choose… |
|-------------|---------|
| General-purpose cloud storage | S3 |
| GCP-native integration | GCS |
| Azure ecosystem | Azure Blob |
| Zero egress / CDN-friendly | Cloudflare R2 |
| Local dev without cloud | Local filesystem |
| Unit tests only | Memory |

## Multi-Backend Configuration

```yaml
storage:
  backends:
    - name: primary
      primary: true
      driver: s3
      s3:
        bucket: my-app-files
        region: us-east-1
    - name: avatars
      driver: s3
      s3:
        bucket: my-app-avatars
        region: us-east-1
```

## Testing with Memory Driver

```python
from lexigram.storage import StorageProvider, StorageConfig

provider = StorageProvider(config=StorageConfig(
    default_driver="memory",
    drivers={"memory": {}},
))
```

The `validate_production_security()` method on `StorageConfig` detects placeholder credentials and raises `ValueError` in production environments — keeping your deployment safe from accidentally shipped default secrets.
