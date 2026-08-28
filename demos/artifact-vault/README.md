# Storage — Artifact Vault

A focused, browser-first example of **Lexigram StorageModule**. It uses only
the storage domain module plus `WebModule`, with the package's deterministic
in-memory blob driver and no cloud credentials.

## What to try

1. Upload a text, Markdown, or JSON artifact.
2. Inspect object metadata, including size, content type, owner, and ETag.
3. Preview and delete objects from the browser.
4. Open **Access** to see the active driver's public URL and its honest
   presigned-URL capability.

## Lexigram surface

- `StorageModule.configure()` and `StorageProvider` lifecycle
- DI-injected `BlobStoreProtocol`
- `UploadOptions` metadata and content-type handling
- upload, list, info, download, delete, URL, and health operations
- `WebModule` controllers with a standalone server entry point

The memory driver intentionally reports that presigned URLs are unavailable;
use a cloud driver for real signed access. The rest of the object API is the
same, which makes the demo safe to run offline.

## Run

```bash
cd demos/artifact-vault
PYTHONPATH=src uv run python -m artifact_vault
```

The hub embeds this console at `/demos/artifact-vault/`.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/artifacts` | List object metadata |
| POST | `/api/artifacts/upload` | Upload an artifact |
| GET | `/api/artifacts/content/{name}` | Download and preview text |
| GET | `/api/artifacts/access/{name}` | Show URL and signed access support |
| DELETE | `/api/artifacts/{name}` | Delete an object |
| GET | `/api/artifacts/health` | Check the active storage backend |
