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
from lexigram.secrets.backends.registry import SecretsBackendRegistry
from lexigram.secrets.config import SecretsConfig
from lexigram.secrets.exceptions import SecretConfigError
from lexigram.secrets.rotation import RotationDecorator, RotationSchedule
from lexigram.secrets.tenancy import TenantScopedSecretStore
from lexigram.secrets.types import RotatableSecretStoreProtocol


class SecretsProvider(Provider):
    """Registers and bootstraps the secrets rotation subsystem.

    Registers a ``RotatableSecretStoreProtocol`` singleton (optionally
    wrapped in a ``TenantScopedSecretStore``) and a ``RotationDecorator``
    that applies the configured rotation schedule.

    Dual-mode configuration: an explicit ``config`` wins; otherwise the
    typed ``secrets`` yaml section injected by the orchestrator (via
    ``config_key``) is used; otherwise defaults apply.
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
        # Keep _config None for zero-config construction so the orchestrator
        # can inject the yaml section via the ``config`` property before
        # register(); register() resolves explicit > injected > default.
        self._requested_config = config
        self._config: SecretsConfig | None = config
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
        injected = self.config if isinstance(self.config, SecretsConfig) else None
        self._config = self._requested_config or injected or SecretsConfig()
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
        if self._config is None or not self._config.enabled:
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
        options = dict(config.backend_options)
        if config.backend_type == "vault":
            if not options.get("token", ""):
                raise SecretConfigError(
                    "vault backend requires a non-empty 'token' in backend_options "
                    "before registration (D1 fail-closed)"
                )
        elif config.backend_type == "aws":
            aws_access_key_id = options.get("aws_access_key_id")
            aws_secret_access_key = options.get("aws_secret_access_key")
            if (aws_access_key_id is None) != (aws_secret_access_key is None):
                raise SecretConfigError(
                    "aws backend requires both 'aws_access_key_id' and "
                    "'aws_secret_access_key' in backend_options, or neither "
                    "(to use ambient credentials) (D1 fail-closed)"
                )
        elif config.backend_type == "gcp":
            if not options.get("project_id", ""):
                raise SecretConfigError(
                    "gcp backend requires a non-empty 'project_id' in backend_options "
                    "before registration (D1 fail-closed)"
                )
        elif config.backend_type == "azure":
            if not options.get("vault_url", ""):
                raise SecretConfigError(
                    "azure backend requires a non-empty 'vault_url' in backend_options "
                    "before registration (D1 fail-closed)"
                )

        registry = SecretsBackendRegistry.with_defaults()
        return registry.create_store(config.backend_type, options)
