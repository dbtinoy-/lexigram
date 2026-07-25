"""Observability DI provider."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ai.observability.config import ObservabilityConfig
from lexigram.ai.observability.health import AIHealthMonitor
from lexigram.ai.observability.metrics import AIMetrics
from lexigram.ai.observability.tracing import AITracer
from lexigram.contracts.ai import LLMClientProtocol
from lexigram.contracts.ai.governance import AIAuditStoreProtocol
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.contracts.data.vector.protocols import VectorStoreProtocol
from lexigram.contracts.exceptions.container import UnresolvableDependencyError
from lexigram.contracts.observability.ai import (
    AIHealthMonitorProtocol,
    AIMetricsProtocol,
    AITracerProtocol,
)
from lexigram.di.provider import Provider
from lexigram.logging import (
    get_logger,
)
from lexigram.logging.redaction import DefaultRedactor

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        BootContainerProtocol,
        ContainerRegistrarProtocol,
    )

logger = get_logger(__name__)


class ObservabilityProvider(Provider):
    """Provider for AI Observability.

    Registers :class:`~lexigram.ai.observability.metrics.AIMetrics`,
    :class:`~lexigram.ai.observability.tracing.AITracer`, and
    :class:`~lexigram.ai.observability.health.AIHealthMonitor`.

    During ``boot()``, self-wires observability decorators around any
    ``LLMClientProtocol`` and ``VectorStoreProtocol`` that are already
    registered in the container, so the wrapping is transparent to callers.
    """

    name = "ai-observability"
    priority = ProviderPriority.DOMAIN
    config_key: str | None = "ai_observability"
    config_model: type | None = ObservabilityConfig

    def __init__(self, config: ObservabilityConfig | None = None) -> None:
        super().__init__()
        self._requested_config = config
        self._config = config or ObservabilityConfig()

    @classmethod
    def from_config(
        cls, config: ObservabilityConfig, **context
    ) -> ObservabilityProvider:
        """Factory method for DI container setup."""
        return cls(config)

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register the observability services."""
        self._config = self._requested_config or (
            self.config
            if isinstance(getattr(self, "config", None), ObservabilityConfig)
            else self._config
        )
        container.singleton(ObservabilityConfig, self._config)

        if not self._config.enabled:
            logger.info(
                "observability_disabled", reason="ObservabilityConfig.enabled=False"
            )
            return

        # Register singletons for the core observability classes.
        # Also register under the contracts protocols so callers resolved
        # by protocol receive the same instances.
        container.singleton(AIMetrics)
        container.singleton(AIMetricsProtocol, AIMetrics)
        redaction_policy = (
            DefaultRedactor() if self._config.trace_redaction_enabled else None
        )
        max_attribute_length = (
            self._config.trace_max_attribute_length
            if self._config.trace_max_attribute_length > 0
            else None
        )
        if redaction_policy is None and max_attribute_length is None:
            container.singleton(AITracer)
            container.singleton(AITracerProtocol, AITracer)
        else:
            tracer_instance = AITracer(
                redaction_policy=redaction_policy,
                max_attribute_length=max_attribute_length,
            )
            container.singleton(AITracer, tracer_instance)
            container.singleton(AITracerProtocol, tracer_instance)
        container.singleton(AIHealthMonitor)
        container.singleton(AIHealthMonitorProtocol, AIHealthMonitor)

        logger.info("observability_registered")

    async def boot(self, container: BootContainerProtocol) -> None:
        """Boot phase — self-wire observability wrappers into the container.

        If ``LLMClientProtocol`` or ``VectorStoreProtocol`` are registered,
        they are replaced with instrumented wrappers.  Both ``AITracer`` and
        ``AIMetrics`` must be available; if either is missing the wrapping is
        skipped gracefully.
        """
        if not self._config.enabled:
            logger.debug("observability_booted_skipped", reason="disabled")
            return

        tracer: AITracer | None = None
        metrics: AIMetrics | None = None
        audit_store: Any | None = None

        try:
            tracer = await container.resolve(AITracer)
            metrics = await container.resolve(AIMetrics)
        except (ValueError, KeyError, TypeError):
            logger.debug("observability_tracer_metrics_unavailable")

        try:
            audit_store = await container.resolve(AIAuditStoreProtocol)
        except (ValueError, KeyError, TypeError, UnresolvableDependencyError):
            pass  # audit store is optional

        # Wrap LLM client if registered
        if tracer or metrics:
            try:
                raw_llm = await container.resolve(LLMClientProtocol)
                from lexigram.ai.observability.wrappers import ObservableLLMClient

                observable_llm = ObservableLLMClient(
                    raw_llm,
                    provider=getattr(raw_llm, "_provider", "unknown"),
                    model=getattr(raw_llm, "_model", "unknown"),
                    tracer=tracer,
                    metrics=metrics,
                    audit_store=audit_store,
                    redaction_policy=(
                        DefaultRedactor()
                        if self._config.trace_redaction_enabled
                        else None
                    ),
                )
                container.bind(LLMClientProtocol, observable_llm)
                logger.info("observability_llm_wrapped")
            except (ValueError, KeyError, TypeError, UnresolvableDependencyError):
                logger.debug("observability_no_llm_to_wrap")

            # Wrap vector store if registered
            try:
                raw_store = await container.resolve(VectorStoreProtocol)
                from lexigram.ai.observability.wrappers import ObservableVectorStore

                observable_store = ObservableVectorStore(
                    raw_store,
                    backend=getattr(raw_store, "_backend", "unknown"),
                    collection=getattr(raw_store, "_collection", "unknown"),
                    tracer=tracer,
                    metrics=metrics,
                )
                container.bind(VectorStoreProtocol, observable_store)
                logger.info("observability_vector_wrapped")
            except (ValueError, KeyError, TypeError, UnresolvableDependencyError):
                logger.debug("observability_no_vector_to_wrap")

        logger.debug("observability_booted")

    async def shutdown(self) -> None:
        """Shutdown phase."""
        logger.debug("observability_shutdown")

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Health check — always healthy (in-process domain provider).

        No external backend to ping.

        Args:
            timeout: Ignored for in-process providers.

        Returns:
            Always HEALTHY — no external backend to ping.
        """
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            details={"status": "operational"},
        )


__all__ = ["ObservabilityProvider"]
