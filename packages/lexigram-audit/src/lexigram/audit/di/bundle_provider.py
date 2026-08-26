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
    AuditSchedulingProvider, and optionally AuditAdminProvider.

    Args:
        config: Audit configuration. When ``None``, the orchestrator injects
            the typed ``audit`` yaml section after construction and
            sub-providers are composed in :meth:`register`.
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
        self.config = config
        self._enable_admin = enable_admin
        self._sub_providers: list[Provider] = []
        if config is not None:
            # Explicit config: compose eagerly. Zero-config construction
            # defers to register(), after the orchestrator has injected
            # the yaml section.
            self._compose_sub_providers()

    def _compose_sub_providers(self) -> None:
        """(Re)build sub-providers from the current ``self.config``.

        Called from ``__init__`` (explicit config) and lazily from
        ``register()`` when the orchestrator injected the yaml section
        after construction. Recomposition before any ``register()`` call
        is safe — nothing has been registered yet.
        """
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

        cfg = self.config
        include_admin = self._enable_admin and (cfg is None or cfg.enable_admin)
        self._sub_providers = [
            AuditCoreProvider(config=cfg),
            AuditRetentionProvider(config=cfg),
            AuditVerifierProvider(config=cfg),
            AuditSchedulingProvider(config=cfg),
        ]
        if include_admin:
            self._sub_providers.append(AuditAdminProvider(config=cfg))

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Delegate registration to all sub-providers.

        Late config binding: the orchestrator injects the typed ``audit``
        section (via ``config_key``) after construction and before this
        call. If ``configure()`` ran with no explicit config, compose now so
        the automatic path behaves identically to the explicit one.
        """
        if not self._sub_providers:
            self._compose_sub_providers()
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
