---
title: lexigram-storage Troubleshooting
description: Common errors, their causes, and fixes.
---

## File Not Found

**Error:** `StorageFileNotFoundError` — "File not found"

**Cause:** The path doesn't exist in the storage backend.

**Fix:**
- Verify the path: `await store.exists("path/to/file")`.
- Check prefix and naming conventions.
- For S3, verify the bucket and key exist in the AWS console.

## Bucket / Container Not Found (S3, GCS, Azure)

**Error:** `StorageUnavailableError` or driver-specific `NoSuchBucket` / `ContainerNotFound`

**Cause:** The bucket/container hasn't been created, or the name is wrong.

**Fix:**
- For S3: `aws s3 mb s3://myapp-bucket --region us-east-1`.
- For GCS: `gsutil mb gs://myapp-bucket`.
- For Azure: create the container via Azure Portal or CLI.
- For R2: create the bucket via the Cloudflare dashboard.

## Presigned URL Generation Fails

**Error:** `StorageUnsupportedOperationError` or `ValueError`

**Cause:** The driver doesn't support presigned URLs (local, memory).

**Fix:**
- Presigned URLs are only available on S3-like backends (S3, R2).
- For local files, use `store.get_url()` which returns the `base_url` + path.
- For GCS, check that credentials have `iam.serviceAccounts.signBlob` permission.

## Authentication Error (S3, GCS, Azure)

**Error:** `StorageUnavailableError` with "Access Denied" or "403"

**Cause:** Wrong credentials or insufficient IAM permissions.

**Fix:**
- Verify `access_key`/`secret_key` for S3/R2, `credentials_path` for GCS, or `account_key` for Azure.
- Check the IAM policy includes `s3:PutObject`, `s3:GetObject`, etc.
- For GCS, ensure the service account has `storage.objectAdmin` role.
- For Azure, verify the account key is correct and the account is active.

## Invalid Path

**Error:** `InvalidPathError` — "Path is invalid or attempts directory traversal"

**Cause:** The path contains `..` or other directory traversal patterns.

**Fix:**
- Sanitize input paths before passing to storage methods.
- Use the path utilities from `lexigram.storage.lib.paths`.

## File Too Large

**Error:** `QuotaExceededError` or upload silently fails

**Cause:** File exceeds `service.max_file_size_mb` or the cloud provider's limit.

**Fix:**
```yaml
storage:
  service:
    max_file_size_mb: 500  # increase as needed
```
For large files, use `stream()` to upload in chunks.

## Unspported Operation

**Error:** `StorageUnsupportedOperationError`

**Cause:** The driver doesn't support the requested operation (e.g., `copy` on memory driver).

**Fix:**
- Check which driver you are using (S3 supports copy, memory does not).
- Implement the operation manually (download + re-upload).

## Multi-Backend: Named Store Not Found

**Error:** Container resolution fails for `Annotated[BlobStoreProtocol, Named("...")]`

**Cause:** The named backend isn't in `storage.backends` or the name doesn't match.

**Fix:**
- Verify the name in `Named(...)` matches a `name` field in `storage.backends`.
- Ensure `backends` is configured in your YAML.

## Checksum Mismatch

**Error:** `ChecksumMismatchError`

**Cause:** Downloaded file content doesn't match the expected checksum.

**Fix:**
- Re-download the file: transient corruption is rare on cloud backends.
- Verify the upload completed successfully (check `FileInfo.etag`).
- For local storage, check disk integrity.
