"""Composite AuditBundleProvider wiring all audit sub-providers."""

from __future__ import annotations

from lexigram.audit.config import AuditConfig
from lexigram.contracts.core.di import (
    BootContainerProtocol,
    ContainerRegistrarProtocol,
)
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.di.provider import Provider

__all__ = ["AuditBundleProvider"]


class AuditBundleProvider(Provider):
    """Composite provider that wires the full Lexigram audit stack.

    Composes AuditCoreProvider, AuditRetentionProvider, AuditVerifierProvider,
    and optionally AuditAdminProvider.

    Args:
        config: Audit configuration. Defaults to AuditConfig() if not provided.
        enable_admin: Whether to register the admin panel contributor.
    """

    # config_key + config_model MUST be set together — the orchestrator's
    # _inject_provider_config hook raises ConfigurationError when only one is
    # present (see lexigram/di/orchestrator/lifecycle.py::_inject_provider_config).
    config_key: str | None = "audit"
    config_model: type | None = AuditConfig

    def __init__(
        self,
        config: AuditConfig | None = None,
        enable_admin: bool = True,
    ) -> None:
        super().__init__(name="audit_bundle", priority=ProviderPriority.INFRASTRUCTURE)
        from lexigram.audit.di.sub_providers.admin_provider import AuditAdminProvider
        from lexigram.audit.di.sub_providers.core_provider import AuditCoreProvider
        from lexigram.audit.di.sub_providers.retention_provider import (
            AuditRetentionProvider,
        )
        from lexigram.audit.di.sub_providers.scheduling_provider import (
            AuditSchedulingProvider,
        )
        from lexigram.audit.di.sub_providers.verifier_provider import (
            AuditVerifierProvider,
        )

        self._sub_providers: list[Provider] = [
            AuditCoreProvider(config=config),
            AuditRetentionProvider(config=config),
            AuditVerifierProvider(config=config),
            AuditSchedulingProvider(config=config),
        ]
        if enable_admin:
            self._sub_providers.append(AuditAdminProvider(config=config))

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Delegate registration to all sub-providers."""
        for provider in self._sub_providers:
            await provider.register(container)

    async def boot(self, container: BootContainerProtocol) -> None:
        """Delegate boot to all sub-providers."""
        for provider in self._sub_providers:
            await provider.boot(container)

    async def shutdown(self) -> None:
        """Shutdown in reverse registration order."""
        for provider in reversed(self._sub_providers):
            await provider.shutdown()
