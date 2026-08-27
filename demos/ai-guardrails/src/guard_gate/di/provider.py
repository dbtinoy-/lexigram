"""DI wiring for the ai-guardrails demo.

A Provider tells the DI container *what* exists and *how* to build it.
Two-phase lifecycle: ``register()`` binds, ``boot()`` initializes.

This is YOUR provider — it registers domain services only.
Framework services (GuardPipeline, Governance) are registered by their
own modules (GuardModule, GovernanceModule).  Your provider bridges
them into your domain objects.
"""

from __future__ import annotations

from guard_gate.domain.guarded_assistant import GuardedAssistant
from guard_gate.domain.policy import PolicyToggle
from guard_gate.repository.acts import COST_PER_TURN
from lexigram.ai.governance import AIAuditStore
from lexigram.contracts.ai import AIGovernanceProtocol
from lexigram.contracts.core.di import (
    BootContainerProtocol,
    ContainerRegistrarProtocol,
)
from lexigram.contracts.exceptions import UnresolvableDependencyError
from lexigram.di.provider import Provider
from lexigram.logging import get_logger

logger = get_logger(__name__)

__all__ = ["GuardrailsProvider"]


class GuardrailsProvider(Provider):
    """Wire the guardrails services; assembly runs at boot.

    Provider naming convention is <Domain>Provider.
    The `name` attribute identifies this provider in logs/diagnostics.
    register() does NO I/O — it only binds factories/instances.
    boot() is where you connect to databases, warm caches, etc.
    """

    name = "guard-assistant"

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind demo services — no I/O here.

        container.singleton() registers a single shared instance.
        Use container.transient() for per-request instances, or
        container.scoped() for per-request-but-shared-within-scope.

        The factory function (build_assistant) runs at RESOLUTION time,
        not registration time — this is how you defer I/O until boot.
        """
        toggle = PolicyToggle()
        container.singleton(PolicyToggle, instance=toggle)

        async def build_assistant(resolver):
            from lexigram.ai.governance import GovernanceConfig, InMemoryAuditStore
            from lexigram.contracts.ai import GuardPipelineProtocol

            pipeline = await resolver.resolve(GuardPipelineProtocol)
            governance = await resolver.resolve(AIGovernanceProtocol)
            gov_config = await resolver.resolve(GovernanceConfig)

            # GovernanceModule registers InMemoryAuditStore; fall back
            # if someone runs without governance.
            try:
                audit_store = await resolver.resolve(AIAuditStore)
            except UnresolvableDependencyError:
                audit_store = InMemoryAuditStore()

            return GuardedAssistant(
                pipeline=pipeline,
                governance=governance,
                audit_store=audit_store,
                monthly_budget=float(gov_config.monthly_budget or 0.50),
                restricted_models=list(gov_config.restricted_models),
                toggle=toggle,
                cost_per_turn=COST_PER_TURN,
            )

        container.singleton(GuardedAssistant, factory=build_assistant)

    async def boot(self, container: BootContainerProtocol) -> None:
        """Post-registration setup — I/O allowed here.

        boot() runs AFTER all providers have registered.
        The container is frozen — you can resolve but not register.
        This demo has no boot-time I/O, but a real app would connect
        databases, prefetch config, or warm caches here.
        """
        logger.info("guardrails_provider.booted")
