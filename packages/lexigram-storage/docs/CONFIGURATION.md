---
title: lexigram-storage Configuration
description: Every configuration key, its type, default, and environment variable.
---

Config section: `storage:`
Env prefix: `LEX_STORAGE__`

## StorageConfig (Top Level)

| Key | Type | Default | Env Variable | Description |
|-----|------|---------|-------------|-------------|
| `name` | `str` | `"storage"` | `LEX_STORAGE__NAME` | Configuration name |
| `enabled` | `bool` | `true` | `LEX_STORAGE__ENABLED` | Enable storage module |
| `default_driver` | `str` | `"local"` | `LEX_STORAGE__DEFAULT_DRIVER` | Default driver (`local`, `s3`, `gcs`, `azure`, `r2`, `memory`) |
| `health_check_timeout` | `float` | `5.0` | `LEX_STORAGE__HEALTH_CHECK_TIMEOUT` | Health check timeout (seconds) |
| `env` | `str \| None` | `null` | `LEX_STORAGE__ENV` | Environment label |
| `drivers` | `dict` | `{}` | `LEX_STORAGE__DRIVERS__*` | Per-driver configuration |
| `service` | `StorageOperationConfig` | defaults | `LEX_STORAGE__SERVICE__*` | Operation settings |
| `backends` | `list[NamedStorageConfig]` | `[]` | See below | Named multi-backend entries |

## Driver-Specific Configs

### StorageLocalConfig

| Key | Type | Default | Env Variable | Description |
|-----|------|---------|-------------|-------------|
| `root_dir` | `str` | `"./storage"` | `LEX_STORAGE__DRIVERS__LOCAL__ROOT_DIR` | Root directory for files |
| `base_url` | `str` | `"http://localhost:8000/storage"` | `LEX_STORAGE__DRIVERS__LOCAL__BASE_URL` | Base URL for file access |

### StorageS3Config

| Key | Type | Default | Env | Description |
|-----|------|---------|-----|-------------|
| `bucket` | `str` | *(required)* | `LEX_STORAGE__DRIVERS__S3__BUCKET` | S3 bucket name |
| `region` | `str` | *(required)* | `LEX_STORAGE__DRIVERS__S3__REGION` | AWS region |
| `access_key` | `SecretStr \| None` | `null` | `LEX_STORAGE__DRIVERS__S3__ACCESS_KEY` | AWS access key |
| `secret_key` | `SecretStr \| None` | `null` | `LEX_STORAGE__DRIVERS__S3__SECRET_KEY` | AWS secret key |
| `endpoint_url` | `str \| None` | `null` | `LEX_STORAGE__DRIVERS__S3__ENDPOINT_URL` | Custom endpoint (MinIO, etc.) |
| `public_url` | `str \| None` | `null` | `LEX_STORAGE__DRIVERS__S3__PUBLIC_URL` | Custom public URL (R2 custom domain) |
| `encryption` | `EncryptionConfig` | defaults | `LEX_STORAGE__DRIVERS__S3__ENCRYPTION__*` | Server-side encryption |

### StorageGCSConfig

| Key | Type | Default | Env | Description |
|-----|------|---------|-----|-------------|
| `bucket` | `str` | *(required)* | `LEX_STORAGE__DRIVERS__GCS__BUCKET` | GCS bucket name |
| `project_id` | `str` | *(required)* | `LEX_STORAGE__DRIVERS__GCS__PROJECT_ID` | GCP project ID |
| `credentials_path` | `str \| None` | `null` | `LEX_STORAGE__DRIVERS__GCS__CREDENTIALS_PATH` | Service account key path |
| `encryption` | `EncryptionConfig` | defaults | `LEX_STORAGE__DRIVERS__GCS__ENCRYPTION__*` | Server-side encryption |

### StorageAzureConfig

| Key | Type | Default | Env | Description |
|-----|------|---------|-----|-------------|
| `account_name` | `str` | *(required)* | `LEX_STORAGE__DRIVERS__AZURE__ACCOUNT_NAME` | Azure storage account name |
| `account_key` | `SecretStr` | *(required)* | `LEX_STORAGE__DRIVERS__AZURE__ACCOUNT_KEY` | Azure storage account key |
| `container` | `str` | *(required)* | `LEX_STORAGE__DRIVERS__AZURE__CONTAINER` | Blob container name |

### StorageR2Config

| Key | Type | Default | Env | Description |
|-----|------|---------|-----|-------------|
| `bucket` | `str` | *(required)* | `LEX_STORAGE__DRIVERS__R2__BUCKET` | R2 bucket name |
| `access_key` | `SecretStr` | *(required)* | `LEX_STORAGE__DRIVERS__R2__ACCESS_KEY` | R2 access key ID |
| `secret_key` | `SecretStr` | *(required)* | `LEX_STORAGE__DRIVERS__R2__SECRET_KEY` | R2 secret access key |
| `endpoint_url` | `str` | *(required)* | `LEX_STORAGE__DRIVERS__R2__ENDPOINT_URL` | R2 S3-compatible API endpoint |
| `public_url` | `str \| None` | `null` | `LEX_STORAGE__DRIVERS__R2__PUBLIC_URL` | Custom domain for public access |
| `region` | `str` | `"auto"` | `LEX_STORAGE__DRIVERS__R2__REGION` | R2 region |

### EncryptionConfig

| Key | Type | Default | Env | Description |
|-----|------|---------|-----|-------------|
| `enabled` | `bool` | `false` | `LEX_STORAGE__...__ENCRYPTION__ENABLED` | Enable SSE |
| `type` | `str` | `"AES256"` | `LEX_STORAGE__...__ENCRYPTION__TYPE` | Encryption type (`AES256`, `aws:kms`, `gcs:cmek`) |
| `kms_key_id` | `str \| None` | `null` | `LEX_STORAGE__...__ENCRYPTION__KMS_KEY_ID` | KMS/CMEK key ARN or ID |

### StorageOperationConfig

| Key | Type | Default | Env | Description |
|-----|------|---------|-----|-------------|
| `max_file_size_mb` | `int` | `10` | `LEX_STORAGE__SERVICE__MAX_FILE_SIZE_MB` | Max file size in MB |
| `allowed_mime_types` | `list[str]` | `["image/jpeg", "image/png", "image/gif", "image/webp"]` | `LEX_STORAGE__SERVICE__ALLOWED_MIME_TYPES` | Allowed MIME types for upload |

---

## Minimal YAML Example

```yaml
storage:
  default_driver: local
  drivers:
    local:
      root_dir: ./storage/data
```

## Production YAML Example (S3)

```yaml
storage:
  default_driver: s3
  drivers:
    s3:
      bucket: myapp-production
      region: us-west-2
      encryption:
        enabled: true
        type: AES256
  service:
    max_file_size_mb: 100
    allowed_mime_types:
      - '*/*'
```

## Multi-Backend Example

```yaml
storage:
  backends:
    - name: avatars
      driver: s3
      primary: true
      s3:
        bucket: myapp-avatars
        region: us-east-1
    - name: exports
      driver: s3
      s3:
        bucket: myapp-exports
        region: us-east-1
```

## Environment Variable Override

```bash
export LEX_STORAGE__DEFAULT_DRIVER="s3"
export LEX_STORAGE__DRIVERS__S3__BUCKET="myapp-production"
export LEX_STORAGE__DRIVERS__S3__REGION="us-west-2"
export LEX_STORAGE__SERVICE__MAX_FILE_SIZE_MB=100
```
