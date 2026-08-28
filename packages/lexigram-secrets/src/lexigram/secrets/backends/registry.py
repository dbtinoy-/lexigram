"""Secret backend registry — registry-based dispatch of secret stores."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from lexigram.secrets.constants import (
    DEFAULT_VAULT_MOUNT_POINT,
    DEFAULT_VAULT_URL,
    ERROR_UNKNOWN_BACKEND,
)
from lexigram.secrets.types import RotatableSecretStoreProtocol

SecretStoreBuilder = Callable[[dict[str, Any]], RotatableSecretStoreProtocol]


class SecretsBackendRegistry:
    """Registry of secret-store builders, keyed by backend type.

    Each backend type maps to a builder that constructs the corresponding
    store from validated ``backend_options``. Fail-closed validation is a
    provider concern and stays out of this registry.

    Usage::

        registry = SecretsBackendRegistry.with_defaults()
        store = registry.create_store("vault", {"token": "hvs.token"})
    """

    def __init__(self) -> None:
        """Initialise an empty backend registry."""
        self._builders: dict[str, SecretStoreBuilder] = {}

    @classmethod
    def with_defaults(cls) -> SecretsBackendRegistry:
        """Return a registry populated with the built-in secret backends.

        Returns:
            A :class:`SecretsBackendRegistry` pre-registered for memory,
            vault, aws, gcp, and azure.
        """
        registry = cls()

        def _memory(_options: dict[str, Any]) -> RotatableSecretStoreProtocol:
            from lexigram.secrets.backends.memory import (
                InMemoryRotatableSecretStore,
            )

            return InMemoryRotatableSecretStore()

        def _vault(options: dict[str, Any]) -> RotatableSecretStoreProtocol:
            from lexigram.secrets.backends.vault import HashicorpVaultStore

            return HashicorpVaultStore(
                url=options.get("url", DEFAULT_VAULT_URL),
                token=options["token"],
                mount_point=options.get("mount_point", DEFAULT_VAULT_MOUNT_POINT),
            )

        def _aws(options: dict[str, Any]) -> RotatableSecretStoreProtocol:
            from lexigram.secrets.backends.aws import AWSSecretsManagerStore

            return AWSSecretsManagerStore(
                region_name=options.get("region_name", "us-east-1"),
                aws_access_key_id=options.get("aws_access_key_id"),
                aws_secret_access_key=options.get("aws_secret_access_key"),
                aws_session_token=options.get("aws_session_token"),
            )

        def _gcp(options: dict[str, Any]) -> RotatableSecretStoreProtocol:
            from lexigram.secrets.backends.gcp import GCPSecretManagerStore

            return GCPSecretManagerStore(project_id=options["project_id"])

        def _azure(options: dict[str, Any]) -> RotatableSecretStoreProtocol:
            from lexigram.secrets.backends.azure import AzureKeyVaultStore

            return AzureKeyVaultStore(
                vault_url=options["vault_url"],
                tenant_id=options.get("tenant_id"),
                client_id=options.get("client_id"),
                client_secret=options.get("client_secret"),
            )

        registry.register("memory", _memory)
        registry.register("vault", _vault)
        registry.register("aws", _aws)
        registry.register("gcp", _gcp)
        registry.register("azure", _azure)
        return registry

    def register(self, backend_type: str, builder: SecretStoreBuilder) -> None:
        """Register a builder under a backend type.

        Args:
            backend_type: Backend type (e.g. ``"vault"``).
            builder: Callable ``(backend_options dict) -> store``.
        """
        self._builders[backend_type] = builder

    def create_store(
        self, backend_type: str, options: dict[str, Any]
    ) -> RotatableSecretStoreProtocol:
        """Build a secret store for a backend type.

        Args:
            backend_type: Backend type to dispatch on.
            options: Validated ``backend_options`` used to construct the store.

        Returns:
            An instantiated secret store.

        Raises:
            ValueError: If *backend_type* is not a registered backend.
        """
        builder = self._builders.get(backend_type)
        if builder is None:
            raise ValueError(ERROR_UNKNOWN_BACKEND.format(backend=backend_type))
        return builder(options)

    def backends(self) -> list[str]:
        """Return the registered backend types.

        Returns:
            List of backend types in registration order.
        """
        return list(self._builders.keys())

    def __contains__(self, backend_type: str) -> bool:
        return backend_type in self._builders


__all__ = ["SecretStoreBuilder", "SecretsBackendRegistry"]
