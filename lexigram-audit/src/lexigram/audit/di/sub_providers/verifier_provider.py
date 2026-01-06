"""Verifier DI provider: registers AuditVerifierProtocol."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.audit import AuditVerifierProtocol
from lexigram.contracts.core.di import (
    BootContainerProtocol,
    ContainerRegistrarProtocol,
)
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.di.provider import Provider

if TYPE_CHECKING:
    from lexigram.audit.config import AuditConfig

__all__ = ["AuditVerifierProvider"]


class AuditVerifierProvider(Provider):
    """Registers AuditVerifierProtocol when HMAC key is configured.

    Args:
        config: Audit configuration.
    """

    def __init__(self, config: AuditConfig | None = None) -> None:
        super().__init__(
            name="audit_verifier", priority=ProviderPriority.INFRASTRUCTURE
        )
        self._config = config

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind verifier if HMAC key is present."""
        from lexigram.audit.config import AuditConfig as _AuditConfig
        from lexigram.audit.verification.verifier import AuditVerifier

        config = self._config or _AuditConfig()
        if config.hmac_key:
            container.singleton(AuditVerifierProtocol, AuditVerifier)

    async def boot(self, container: BootContainerProtocol) -> None:
        pass
