"""DI wiring for the ai-guardrails demo (internal)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.ai.governance import AIGovernanceProtocol
from lexigram.di.provider import Provider

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

from guard_gate.repository.acts import COST_PER_TURN
from guard_gate.services.guarded_assistant import GuardedAssistant
from guard_gate.services.policy import PolicyToggle


class GuardrailsProvider(Provider):
    """Resolves guard + governance contracts and assembles the assistant."""

    name = "guard-assistant"

    def __init__(self) -> None:
        super().__init__()
        self._toggle = PolicyToggle()
        self._assistant: GuardedAssistant | None = None

    def _get_assistant(self) -> GuardedAssistant:
        if self._assistant is None:
            raise RuntimeError("GuardrailsProvider has not been booted yet")
        return self._assistant

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind the toggle eagerly; the assistant resolves in boot()."""
        container.singleton(PolicyToggle, instance=self._toggle)
        container.singleton(GuardedAssistant, factory=self._get_assistant)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Assemble from booted collaborators."""
        from lexigram.ai.governance.audit import AIAuditStore
        from lexigram.ai.governance.config import GovernanceConfig
        from lexigram.contracts.ai.guards import GuardPipelineProtocol

        pipeline = await container.resolve(GuardPipelineProtocol)
        governance = await container.resolve(AIGovernanceProtocol)
        audit_store = await container.resolve_optional(AIAuditStore)
        gov_config = await container.resolve(GovernanceConfig)

        self._assistant = GuardedAssistant(
            pipeline=pipeline,
            governance=governance,
            audit_store=audit_store if audit_store is not None else _fallback_store(),
            monthly_budget=float(gov_config.monthly_budget or 0.50),
            restricted_models=list(gov_config.restricted_models),
            toggle=self._toggle,
            cost_per_turn=COST_PER_TURN,
        )


def _fallback_store() -> AIAuditStore:
    """Governance auto-binds an InMemoryAuditStore; this is a safety net."""
    from lexigram.ai.governance.audit import InMemoryAuditStore

    return InMemoryAuditStore()


__all__ = ["GuardrailsProvider"]
