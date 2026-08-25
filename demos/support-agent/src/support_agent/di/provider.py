"""DI wiring for the support-agent demo (internal)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.ai.agents import AgentExecutorProtocol
from lexigram.contracts.ai.llm import LLMClientProtocol
from lexigram.contracts.core.health import (
    HealthCheckResult,
)
from lexigram.di.provider import Provider

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

from support_agent.repository.scripted_llm import ScriptedLLM
from support_agent.services.support_service import SupportAgent, build_support_agent


class AgentSupportProvider(Provider):
    """Binds the scripted LLM and assembles the facade at boot.

    The LLM binding MUST happen in ``register()``: ``AgentsProvider.boot()``
    performs a required resolve of ``LLMClientProtocol``
    (experimental/ai/lexigram-ai-agents/src/lexigram/ai/agents/di/provider.py:136).
    """

    name = "agent-support"

    def __init__(self) -> None:
        super().__init__()
        self._llm = ScriptedLLM()
        self._support: SupportAgent | None = None

    def _get_llm(self) -> ScriptedLLM:
        """Registered eagerly so freeze-time validation sees it."""
        return self._llm

    def _get_support(self) -> SupportAgent:
        """Valid only after boot() has assembled the facade."""
        if self._support is None:
            raise RuntimeError("AgentSupportProvider has not been booted yet")
        return self._support

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind singletons; collaborators resolve only in boot()."""
        container.singleton(ScriptedLLM, instance=self._llm)
        container.singleton(LLMClientProtocol, factory=self._get_llm)
        container.singleton(SupportAgent, factory=self._get_support)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Assemble the facade from the executor wired by AgentsModule."""
        executor = await container.resolve(AgentExecutorProtocol)
        self._support = SupportAgent(
            executor=executor,
            agent=build_support_agent(),
        )

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report component readiness with live counters."""
        return HealthCheckResult(
            component=self.name,
            details={"scripted_remaining": self._llm.remaining},
        )


__all__ = ["AgentSupportProvider"]
