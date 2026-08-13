# lexigram-secrets

Secret vaults with rotation, tenant isolation, and audit logging for the Lexigram Framework.
Supports HashiCorp Vault, AWS Secrets Manager, GCP Secret Manager, Azure Key Vault, and in-memory
backends with automatic key rotation, version tracking, and tenant-scoped secret stores.

---

## Overview

lexigram-secrets provides a `RotatableSecretStoreProtocol`-based secret management system
with versioned rotation, tenant isolation, audit logging, and pluggable backends. All services
are wired via `SecretsProvider`, which registers the secret store and rotation decorator
with the DI container.

> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)
## Install

```bash
uv add lexigram-secrets
# Optional extras
uv add "lexigram-secrets[vault]"    # HashiCorp Vault backend
uv add "lexigram-secrets[aws]"      # AWS Secrets Manager backend
uv add "lexigram-secrets[gcp]"      # GCP Secret Manager backend
uv add "lexigram-secrets[azure]"    # Azure Key Vault backend
```

## Quick Start

```python
from lexigram import Application
from lexigram.secrets import SecretsModule
from lexigram.secrets.types import RotatableSecretStoreProtocol


async def main() -> None:
    async with Application.boot(modules=[SecretsModule.configure()]) as app:
        store = await app.container.resolve(RotatableSecretStoreProtocol)
        # ... work with the secret store ...


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
```

## Configuration

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `name` | `"secrets"` | `LEX_SECRETS__NAME` | Configuration name |
| `enabled` | `true` | `LEX_SECRETS__ENABLED` | Enable the secrets subsystem |
| `backend_type` | `memory` | `LEX_SECRETS__BACKEND_TYPE` | Backend store type (`memory`, `vault`, `aws`, `gcp`, `azure`) |
| `backend_options` | `{}` | — | Keyword arguments forwarded to the backend constructor |
| `max_age_seconds` | `7776000` | `LEX_SECRETS__MAX_AGE_SECONDS` | Max age before automatic rotation |
| `warning_before_seconds` | `86400` | `LEX_SECRETS__WARNING_BEFORE_SECONDS` | Seconds before expiry to emit warnings |
| `tenant_id` | `null` | `LEX_SECRETS__TENANT_ID` | Optional tenant namespace |
| `audit_actor_id` | `"secrets-system"` | `LEX_SECRETS__AUDIT_ACTOR_ID` | Actor identifier for audit logs |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `SecretsModule.configure(config)` | Configure with explicit SecretsConfig |
| `SecretsModule.stub()` | Minimal config for testing (memory backend) |

## Key Features

- **Versioned secrets** — Every `set` and `rotate` creates a new version; full history retained
- **Automatic rotation** — `RotationDecorator` (`get_rotated`, `get_current_version`, `check_warnings`) serves a fresh secret when the current version is past `max_age_seconds`
- **Tenant isolation** — `TenantScopedSecretStore` prefixes keys per tenant for multi-tenant apps
- **Audit logging** — `SecretAuditDecorator` logs all store operations through `AuditLoggerProtocol`
- **Pluggable backends** — `HashicorpVaultStore` (KV v2) and in-memory (`FakeRotatableSecretStore`)
- **Bulk operations** — `get_bulk` for fetching multiple secrets at once
- **Version introspection** — `list_versions` and `get_version` for audit and rollback workflows

## Testing

```python
from lexigram.testing.fakes import FakeRotatableSecretStore
from lexigram.testing.compliance import StoreConformanceSuite


class TestMyStore(StoreConformanceSuite):
    @pytest.fixture
    def make_store(self):
        return FakeRotatableSecretStore
```

## Key Source Files

| File | What it contains |
|------|----------------|
| `src/lexigram/secrets/module.py` | `SecretsModule` class with factory methods |
| `src/lexigram/secrets/di/provider.py` | `SecretsProvider` — wires secret store into DI container |
| `src/lexigram/secrets/config.py` | `SecretsConfig` and backend selection |
| `src/lexigram/secrets/types.py` | `RotatableSecretStoreProtocol`, `VersionedSecret`, `SecretVersion` |
| `src/lexigram/secrets/rotation/` | `RotationDecorator` and `RotationSchedule` for automatic key rotation |
| `src/lexigram/secrets/tenancy/` | `TenantScopedSecretStore` for multi-tenant key isolation |
| `src/lexigram/secrets/audit/` | `SecretAuditDecorator` for operation audit logging |
| `src/lexigram/secrets/backends/` | Backend implementations (Vault, etc.) |
