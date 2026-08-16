"""Secrets provider — registers and bootstraps the rotation subsystem."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )
    from lexigram.contracts.core.health import HealthCheckResult

from lexigram.di.provider import Provider, ProviderPriority
from lexigram.secrets.config import SecretsConfig
from lexigram.secrets.constants import (
    DEFAULT_VAULT_MOUNT_POINT,
    DEFAULT_VAULT_URL,
    ERROR_UNKNOWN_BACKEND,
)
from lexigram.secrets.exceptions import SecretConfigError
from lexigram.secrets.rotation import RotationDecorator, RotationSchedule
from lexigram.secrets.tenancy import TenantScopedSecretStore
from lexigram.secrets.types import RotatableSecretStoreProtocol


class SecretsProvider(Provider):
    """Registers and bootstraps the secrets rotation subsystem.

    Registers a ``RotatableSecretStoreProtocol`` singleton (optionally
    wrapped in a ``TenantScopedSecretStore``) and a ``RotationDecorator``
    that applies the configured rotation schedule.
    """

    name = "secrets"
    priority = ProviderPriority.DOMAIN
    config_key: str | None = "secrets"
    config_model: type | None = SecretsConfig

    def __init__(
        self,
        config: SecretsConfig | None = None,
        store: RotatableSecretStoreProtocol | None = None,
    ) -> None:
        # Provider.__init__ initializes self._state and self._config (= None).
        # We must call super first so the lifecycle's state-machine reads
        # (ProviderState.CREATED → REGISTERED → BOOTED) work; without this
        # accessing self.state raises AttributeError at boot time.
        super().__init__()
        # Override the default _config = None set by Provider.__init__ with the
        # explicit SecretsConfig passed at construction time. If a
        # LexigramConfig is registered, the framework's config-injector hook
        # overwrites this via the ``config`` property setter just before
        # register() runs.
        self._config = config or SecretsConfig()
        self._store_override = store

    @classmethod
    def from_config(
        cls,
        config: SecretsConfig,
        **context: Any,
    ) -> SecretsProvider:
        store: RotatableSecretStoreProtocol | None = context.get("store")
        return cls(config=config, store=store)

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        container.singleton(SecretsConfig, self._config)
        if not self._config.enabled:
            return

        store = self._store_override or self._create_store(self._config)

        tenant_id = self._config.tenant_id
        if tenant_id:
            store = TenantScopedSecretStore(store, tenant_id)

        container.singleton(RotatableSecretStoreProtocol, store)

        schedule = RotationSchedule(
            max_age_seconds=self._config.max_age_seconds,
            warning_before_seconds=self._config.warning_before_seconds,
        )
        decorator = RotationDecorator(store, schedule)
        container.singleton(RotationDecorator, decorator)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        if not self._config.enabled:
            return
        _ = await container.resolve(RotatableSecretStoreProtocol)

    async def shutdown(self) -> None:
        pass

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        from datetime import UTC, datetime

        from lexigram.contracts.core.health import HealthCheckResult, HealthStatus

        return HealthCheckResult(
            component="secrets",
            status=HealthStatus.HEALTHY,
            message="Secrets subsystem operational",
            checked_at=datetime.now(UTC),
        )

    def _create_store(self, config: SecretsConfig) -> RotatableSecretStoreProtocol:
        if config.backend_type == "memory":
            from lexigram.secrets.backends.memory import InMemoryRotatableSecretStore

            return InMemoryRotatableSecretStore()
        if config.backend_type == "vault":
            token = config.backend_options.get("token", "")
            if not token:
                raise SecretConfigError(
                    "vault backend requires a non-empty 'token' in backend_options "
                    "before registration (D1 fail-closed)"
                )
            from lexigram.secrets.backends.vault import HashicorpVaultStore

            return HashicorpVaultStore(
                url=config.backend_options.get("url", DEFAULT_VAULT_URL),
                token=token,
                mount_point=config.backend_options.get(
                    "mount_point", DEFAULT_VAULT_MOUNT_POINT
                ),
            )
        if config.backend_type == "aws":
            aws_access_key_id = config.backend_options.get("aws_access_key_id")
            aws_secret_access_key = config.backend_options.get("aws_secret_access_key")
            if (aws_access_key_id is None) != (aws_secret_access_key is None):
                raise SecretConfigError(
                    "aws backend requires both 'aws_access_key_id' and "
                    "'aws_secret_access_key' in backend_options, or neither "
                    "(to use ambient credentials) (D1 fail-closed)"
                )
            from lexigram.secrets.backends.aws import AWSSecretsManagerStore

            return AWSSecretsManagerStore(
                region_name=config.backend_options.get("region_name", "us-east-1"),
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=config.backend_options.get("aws_session_token"),
            )
        if config.backend_type == "gcp":
            project_id = config.backend_options.get("project_id", "")
            if not project_id:
                raise SecretConfigError(
                    "gcp backend requires a non-empty 'project_id' in backend_options "
                    "before registration (D1 fail-closed)"
                )
            from lexigram.secrets.backends.gcp import GCPSecretManagerStore

            return GCPSecretManagerStore(project_id=project_id)
        if config.backend_type == "azure":
            vault_url = config.backend_options.get("vault_url", "")
            if not vault_url:
                raise SecretConfigError(
                    "azure backend requires a non-empty 'vault_url' in backend_options "
                    "before registration (D1 fail-closed)"
                )
            from lexigram.secrets.backends.azure import AzureKeyVaultStore

            return AzureKeyVaultStore(
                vault_url=vault_url,
                tenant_id=config.backend_options.get("tenant_id"),
                client_id=config.backend_options.get("client_id"),
                client_secret=config.backend_options.get("client_secret"),
            )
        raise ValueError(ERROR_UNKNOWN_BACKEND.format(backend=config.backend_type))
