"""DI Provider for the AI Evaluation subsystem."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.ai.evaluation.config import EvaluationConfig
from lexigram.contracts.ai.evaluation import EvaluatorProtocol
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.di.provider import Provider, ProviderPriority
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        BootContainerProtocol,
        ContainerRegistrarProtocol,
    )

logger = get_logger(__name__)


class EvaluationProvider(Provider):
    """Registers evaluation services with the DI container."""

    name = "evaluation"
    priority = ProviderPriority.DOMAIN
    config_key: str | None = "ai.evaluation"
    config_model: type | None = EvaluationConfig

    def __init__(self, config: EvaluationConfig | None = None) -> None:
        super().__init__()
        self._config = config or EvaluationConfig()

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        container.singleton(EvaluationConfig, instance=self._config)

        from lexigram.ai.evaluation.evaluators.criteria import CriteriaEvaluator
        from lexigram.ai.evaluation.evaluators.embedding_distance import (
            EmbeddingDistanceEvaluator,
        )
        from lexigram.ai.evaluation.evaluators.qa import QAEvaluator
        from lexigram.ai.evaluation.evaluators.string_distance import (
            StringDistanceEvaluator,
        )
        from lexigram.ai.evaluation.harness.runner import EvaluationHarness

        container.singleton(
            EvaluatorProtocol,
            CriteriaEvaluator(),
            name="criteria",
        )
        container.singleton(
            EvaluatorProtocol,
            QAEvaluator(),
            name="qa",
        )
        container.singleton(
            EvaluatorProtocol,
            StringDistanceEvaluator(),
            name="string_distance",
        )
        container.singleton(
            EvaluatorProtocol,
            EmbeddingDistanceEvaluator(),
            name="embedding_distance",
        )
        container.singleton(EvaluationHarness, EvaluationHarness())

        logger.info("evaluation_provider_registered")

    async def boot(self, container: BootContainerProtocol) -> None:
        logger.info("evaluation_provider_booted")

    async def shutdown(self) -> None:
        pass

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        return HealthCheckResult(
            component="evaluation",
            status=HealthStatus.HEALTHY,
            details={"status": "ok"},
        )


__all__ = ["EvaluationProvider"]
