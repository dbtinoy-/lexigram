"""GuardProtocol DI provider — registers guard pipeline with the container."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from lexigram.ai.guard.config import GuardConfig
from lexigram.ai.guard.input.injection import PromptInjectionDetector
from lexigram.ai.guard.input.length import InputLengthGuard
from lexigram.ai.guard.input.llm_injection import LLMInjectionDetector
from lexigram.ai.guard.input.llm_jailbreak import LLMJailbreakDetector
from lexigram.ai.guard.input.pii import PIIDetector
from lexigram.ai.guard.input.topic import TopicRestrictor
from lexigram.ai.guard.output.length import OutputLengthGuard
from lexigram.ai.guard.output.pii_redactor import PIIRedactor
from lexigram.ai.guard.pipeline.guard_pipeline import GuardPipeline
from lexigram.contracts.ai.guards import (
    GuardPipelineProtocol,
    InputGuardProtocol,
    OutputGuardProtocol,
)
from lexigram.contracts.ai.llm import LLMClientProtocol
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.di.provider import Provider
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

logger = get_logger(__name__)


class GuardProvider(Provider):
    """Provider for the content safety guard pipeline.

    Reads :class:`~lexigram.ai.guard.config.GuardConfig`, builds a
    :class:`~lexigram.ai.guard.pipeline.guard_pipeline.GuardPipeline`
    with the configured guards, and registers it as a singleton.

    When ``GuardConfig.enabled`` is ``False``, a no-op pipeline with no
    guards is registered (all checks pass through).

    When ``GuardConfig.enable_llm_guards`` is ``True`` and an
    ``LLMClientProtocol`` is available in the container (resolved
    optionally during :meth:`boot`), LLM-based injection and jailbreak
    detectors are appended to the pipeline.
    """

    name = "guard"
    priority = ProviderPriority.SECURITY
    config_key: str | None = "ai_guard"
    config_model: type | None = GuardConfig

    def __init__(
        self,
        config: GuardConfig | None = None,
        enable_audit_logging: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__()
        self._requested_config = config
        self._config = config or GuardConfig()
        self._enable_audit_logging = enable_audit_logging
        self._pipeline: GuardPipeline | None = None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register the guard pipeline with the DI container."""
        self._config = self._requested_config or (
            self.config
            if isinstance(getattr(self, "config", None), GuardConfig)
            else self._config
        )
        container.singleton(GuardConfig, self._config)

        if not self._config.enabled:
            logger.info("guard_provider_disabled", reason="GuardConfig.enabled=False")
            pipeline = GuardPipeline()
            self._pipeline = pipeline
            container.singleton(GuardPipeline, pipeline)
            container.singleton(GuardPipelineProtocol, pipeline)
            return

        pipeline = self._build_pipeline()
        self._pipeline = pipeline
        container.singleton(GuardPipeline, pipeline)
        container.singleton(GuardPipelineProtocol, pipeline)
        logger.info(
            "guard_provider_registered",
            input_guards=len(pipeline._input_guards),
            output_guards=len(pipeline._output_guards),
        )

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Boot phase — optionally attach LLM-based guards if configured.

        Resolves ``LLMClientProtocol`` from the container when
        ``GuardConfig.enable_llm_guards`` is ``True``.  If the client is
        not registered, LLM guards are silently skipped.
        """
        if (
            not self._config.enable_llm_guards
            or not self._config.enabled
            or self._pipeline is None
        ):
            logger.debug("guard_provider_booted", llm_guards=False)
            return

        try:
            llm = await container.resolve_optional(LLMClientProtocol)
        except (ImportError, AttributeError, RuntimeError) as exc:
            logger.warning(
                "guard_provider_llm_resolve_failed",
                error=str(exc),
            )
            logger.debug("guard_provider_booted", llm_guards=False)
            return

        if llm is None:
            logger.info(
                "guard_provider_llm_guards_skipped",
                reason="LLMClientProtocol not registered in container",
            )
            logger.debug("guard_provider_booted", llm_guards=False)
            return

        cfg = self._config
        self._pipeline.add_input_guard(
            cast(
                "InputGuardProtocol",
                LLMInjectionDetector(
                    llm,
                    model=cfg.guard_model,
                    threshold=cfg.llm_guard_threshold,
                    action=cfg.injection_action,
                    fail_open=cfg.llm_guard_fail_open,
                ),
            )
        )
        self._pipeline.add_input_guard(
            cast(
                "InputGuardProtocol",
                LLMJailbreakDetector(
                    llm,
                    model=cfg.guard_model,
                    threshold=cfg.llm_guard_threshold,
                    action=cfg.injection_action,
                    fail_open=cfg.llm_guard_fail_open,
                ),
            )
        )
        logger.info(
            "guard_provider_llm_guards_registered",
            model=cfg.guard_model,
            threshold=cfg.llm_guard_threshold,
        )
        logger.debug("guard_provider_booted", llm_guards=True)

    async def shutdown(self) -> None:
        """Shutdown phase — no cleanup required for guard pipeline."""
        logger.debug("guard_provider_shutdown")

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

    def _build_pipeline(self) -> GuardPipeline:
        """Build the heuristic guard pipeline from configuration.

        Returns:
            Configured GuardPipeline instance.
        """
        cfg = self._config

        # ---------- input guards ----------
        input_guards: list[InputGuardProtocol] = []

        if cfg.injection_detection:
            input_guards.append(PromptInjectionDetector(action=cfg.injection_action))

        if cfg.pii_detection:
            entities = cfg.pii_entities or None
            input_guards.append(PIIDetector(action=cfg.pii_action, entities=entities))

        if cfg.max_input_chars > 0:
            input_guards.append(
                InputLengthGuard(
                    max_chars=cfg.max_input_chars, action=cfg.length_action
                )
            )

        if cfg.restricted_topics:
            input_guards.append(
                TopicRestrictor(restricted_topics=cfg.restricted_topics)
            )

        # ---------- output guards ----------
        output_guards: list[OutputGuardProtocol] = []

        if cfg.pii_redaction_output:
            entities = cfg.pii_entities or None
            output_guards.append(PIIRedactor(entities=entities))

        if cfg.max_output_chars > 0:
            output_guards.append(
                OutputLengthGuard(
                    max_chars=cfg.max_output_chars, action=cfg.length_action
                )
            )

        return GuardPipeline(input_guards=input_guards, output_guards=output_guards)


__all__ = ["GuardProvider"]
