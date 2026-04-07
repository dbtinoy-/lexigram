"""Retention DI provider: registers retention policy and purger."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.audit import RetentionPolicyProtocol
from lexigram.contracts.core.di import (
    BootContainerProtocol,
    ContainerRegistrarProtocol,
)
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.di.provider import Provider

if TYPE_CHECKING:
    from lexigram.audit.config import AuditConfig

__all__ = ["AuditRetentionProvider"]


class AuditRetentionProvider(Provider):
    """Registers RetentionPolicyProtocol and AuditPurger.

    Args:
        config: Audit configuration.
    """

    def __init__(self, config: AuditConfig | None = None) -> None:
        super().__init__(
            name="audit_retention", priority=ProviderPriority.INFRASTRUCTURE
        )
        self._config = config

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind retention policy and purger singletons."""
        from lexigram.audit.config import AuditConfig as _AuditConfig
        from lexigram.audit.retention.policy import PolicyBasedRetention
        from lexigram.audit.retention.purge import AuditPurger

        config = self._config or _AuditConfig()

        container.singleton(
            RetentionPolicyProtocol,
            lambda: PolicyBasedRetention(policy=config.retention_policy),
        )
        container.singleton(AuditPurger)

    async def boot(self, container: BootContainerProtocol) -> None:
        pass
