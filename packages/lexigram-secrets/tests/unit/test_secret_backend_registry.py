"""Tests for SecretsBackendRegistry."""

from __future__ import annotations

import pytest

from lexigram.secrets.backends.registry import SecretsBackendRegistry


def test_registry_has_all_default_backends() -> None:
    """with_defaults registers the five built-in secret backends."""
    registry = SecretsBackendRegistry.with_defaults()
    assert set(registry.backends()) == {"memory", "vault", "aws", "gcp", "azure"}


def test_create_store_memory() -> None:
    """The memory backend requires no options."""
    from lexigram.secrets.backends.memory import InMemoryRotatableSecretStore

    store = SecretsBackendRegistry.with_defaults().create_store("memory", {})
    assert isinstance(store, InMemoryRotatableSecretStore)


def test_create_store_vault_applies_defaults() -> None:
    """Vault construction uses option values with defaults."""
    from lexigram.secrets.backends.vault import HashicorpVaultStore

    store = SecretsBackendRegistry.with_defaults().create_store(
        "vault", {"url": "http://vault:8200", "token": "hvs.token"}
    )
    assert isinstance(store, HashicorpVaultStore)
    assert store._url == "http://vault:8200"
    assert store._token == "hvs.token"


def test_create_store_aws() -> None:
    """AWS construction forwards ambient credential options."""
    from lexigram.secrets.backends.aws import AWSSecretsManagerStore

    store = SecretsBackendRegistry.with_defaults().create_store("aws", {})
    assert isinstance(store, AWSSecretsManagerStore)
    assert store._region_name == "us-east-1"


def test_create_store_gcp() -> None:
    """GCP construction requires project_id."""
    from lexigram.secrets.backends.gcp import GCPSecretManagerStore

    store = SecretsBackendRegistry.with_defaults().create_store(
        "gcp", {"project_id": "p1"}
    )
    assert isinstance(store, GCPSecretManagerStore)
    assert store._project_id == "p1"


def test_create_store_azure() -> None:
    """Azure construction forwards vault_url."""
    from lexigram.secrets.backends.azure import AzureKeyVaultStore

    store = SecretsBackendRegistry.with_defaults().create_store(
        "azure", {"vault_url": "https://my-vault.vault.azure.net"}
    )
    assert isinstance(store, AzureKeyVaultStore)
    assert store._vault_url == "https://my-vault.vault.azure.net"


def test_create_store_unknown_backend_raises() -> None:
    """An unknown backend raises the existing message."""
    with pytest.raises(ValueError, match="Unknown backend_type: 'nope'"):
        SecretsBackendRegistry.with_defaults().create_store("nope", {})
