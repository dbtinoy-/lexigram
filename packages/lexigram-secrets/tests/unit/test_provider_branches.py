"""Focused tests for secrets provider backend branches and exception types."""

from __future__ import annotations

import pytest

from lexigram.di.container.container import Container
from lexigram.secrets.backends.aws import AWSSecretsManagerStore
from lexigram.secrets.backends.azure import AzureKeyVaultStore
from lexigram.secrets.backends.gcp import GCPSecretManagerStore
from lexigram.secrets.backends.vault import HashicorpVaultStore
from lexigram.secrets.config import SecretsConfig
from lexigram.secrets.di.provider import SecretsProvider
from lexigram.secrets.exceptions import (
    SecretAccessError,
    SecretBackendError,
    SecretConfigError,
    SecretNotFoundError,
    SecretRotationError,
)
from lexigram.secrets.types import RotatableSecretStoreProtocol


@pytest.mark.asyncio
async def test_provider_vault_backend_with_token_registers() -> None:
    config = SecretsConfig(
        backend_type="vault",
        backend_options={"token": "hvs.token", "url": "http://vault:8200"},
    )
    provider = SecretsProvider(config=config)
    container = Container()
    await provider.register(container)
    container.freeze()
    store = await container.resolve(RotatableSecretStoreProtocol)
    assert isinstance(store, HashicorpVaultStore)


@pytest.mark.asyncio
async def test_provider_aws_backend_both_credentials() -> None:
    config = SecretsConfig(
        backend_type="aws",
        backend_options={
            "aws_access_key_id": "AKIAX",
            "aws_secret_access_key": "sk",
        },
    )
    provider = SecretsProvider(config=config)
    container = Container()
    await provider.register(container)
    container.freeze()
    store = await container.resolve(RotatableSecretStoreProtocol)
    assert isinstance(store, AWSSecretsManagerStore)


@pytest.mark.asyncio
async def test_provider_aws_backend_partial_credentials_raises() -> None:
    config = SecretsConfig(
        backend_type="aws",
        backend_options={"aws_access_key_id": "AKIAX"},
    )
    with pytest.raises(SecretConfigError, match="aws backend requires both"):
        await SecretsProvider(config=config).register(Container())


@pytest.mark.asyncio
async def test_provider_gcp_backend_no_project_raises() -> None:
    config = SecretsConfig(backend_type="gcp")
    with pytest.raises(SecretConfigError, match="project_id"):
        await SecretsProvider(config=config).register(Container())


@pytest.mark.asyncio
async def test_provider_gcp_backend_with_project() -> None:
    config = SecretsConfig(backend_type="gcp", backend_options={"project_id": "p1"})
    provider = SecretsProvider(config=config)
    container = Container()
    await provider.register(container)
    container.freeze()
    store = await container.resolve(RotatableSecretStoreProtocol)
    assert isinstance(store, GCPSecretManagerStore)


@pytest.mark.asyncio
async def test_provider_azure_backend_no_vault_url_raises() -> None:
    config = SecretsConfig(backend_type="azure")
    with pytest.raises(SecretConfigError, match="vault_url"):
        await SecretsProvider(config=config).register(Container())


@pytest.mark.asyncio
async def test_provider_azure_backend_with_vault_url() -> None:
    config = SecretsConfig(
        backend_type="azure",
        backend_options={"vault_url": "https://kv.vault.azure.net"},
    )
    provider = SecretsProvider(config=config)
    container = Container()
    await provider.register(container)
    container.freeze()
    store = await container.resolve(RotatableSecretStoreProtocol)
    assert isinstance(store, AzureKeyVaultStore)


@pytest.mark.asyncio
async def test_provider_unknown_backend_raises() -> None:
    config = SecretsConfig(backend_type="nope")
    with pytest.raises(ValueError, match="Unknown"):
        await SecretsProvider(config=config).register(Container())


@pytest.mark.asyncio
async def test_provider_disabled_boot_skips_resolve() -> None:
    provider = SecretsProvider(config=SecretsConfig(enabled=False))
    container = Container()
    await provider.register(container)
    container.freeze()
    await provider.boot(container)


def test_secret_not_found_error_sets_key() -> None:
    error = SecretNotFoundError("db_pass")
    assert error.key == "db_pass"
    assert "db_pass" in str(error)


def test_secret_rotation_error_sets_fields() -> None:
    error = SecretRotationError("api_key", reason="expired")
    assert error.key == "api_key"
    assert error.reason == "expired"
    assert "expired" in str(error)


def test_exception_hierarchy() -> None:
    assert SecretAccessError().code == "LEX_ERR_SECRET_003"
    assert SecretBackendError().code == "LEX_ERR_SECRET_005"
    assert SecretNotFoundError("x").code == "LEX_ERR_SECRET_002"