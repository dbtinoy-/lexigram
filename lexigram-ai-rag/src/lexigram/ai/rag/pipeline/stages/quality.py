"""Quality assurance stage for response validation."""

from __future__ import annotations

from lexigram.ai.rag.config import QualityAssuranceConfig
from lexigram.ai.rag.pipeline.types import PipelineContext
from lexigram.ai.rag.synthesis import (
    ConfidenceScorer,
    FaithfulnessChecker,
    HallucinationChecker,
    QualityMetrics,
    RelevanceFilter,
)
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class QualityAssuranceStage:
    """Pipeline stage for response quality assurance.

    This stage validates the synthesized response against quality
    thresholds including faithfulness, relevance, and confidence.
    """

    def __init__(self, config: QualityAssuranceConfig):
        """Initialize the quality assurance stage.

        Args:
            config: Quality assurance configuration
        """
        self.config = config
        self.faithfulness_checker = FaithfulnessChecker()
        self.relevance_filter = RelevanceFilter()
        self.hallucination_detector = HallucinationChecker(
            strict_mode=config.hallucination_strict_mode,
        )
        self.confidence_scorer = ConfidenceScorer()

    @property
    def name(self) -> str:
        """Get stage name."""
        return "quality_assurance"

    async def process(self, context: PipelineContext) -> PipelineContext:
        """Process the quality assurance stage.

        Args:
            context: Pipeline context with synthesis result

        Returns:
            Updated context with quality metrics
        """
        if not self.config.enabled:
            logger.info("Quality assurance stage disabled, skipping")
            return context

        # Check if we have a synthesis result
        if context.synthesis_result is None:
            logger.warning("No synthesis result available for quality check")
            context.add_warning("No synthesis result for quality assurance")
            return context

        result = context.synthesis_result
        query = result.query
        response = result.response
        chunks = result.context_chunks

        try:
            logger.info(
                "Starting quality assurance",
                extra={
                    "request_id": context.request_id,
                    "response_length": len(response),
                },
            )

            # Calculate quality metrics
            metrics = await self.confidence_scorer.calculate_quality_metrics(
                query,
                response,
                chunks,
            )

            # Store metrics in context
            context.quality_metrics = metrics

            # Also update synthesis result
            result.quality_metrics = metrics

            logger.info(
                "Quality metrics calculated",
                extra={
                    "request_id": context.request_id,
                    "faithfulness": metrics.faithfulness,
                    "relevance": metrics.relevance,
                    "coherence": metrics.coherence,
                    "confidence": metrics.confidence,
                    "has_hallucinations": metrics.has_hallucinations,
                },
            )

            # Check quality thresholds
            quality_issues = self._check_quality_thresholds(metrics)

            if quality_issues:
                logger.warning(
                    "Quality issues detected",
                    extra={
                        "request_id": context.request_id,
                        "issues": quality_issues,
                    },
                )

                for issue in quality_issues:
                    context.add_warning(f"Quality issue: {issue}")

                # Handle low quality response
                if self.config.reject_low_quality:
                    msg = (
                        f"Response quality below threshold: {', '.join(quality_issues)}"
                    )
                    raise ValueError(
                        msg,
                    )

        except Exception as e:
            logger.exception(
                "Quality assurance failed",
                extra={
                    "request_id": context.request_id,
                    "error": str(e),
                },
            )
            raise

        return context

    def _check_quality_thresholds(self, metrics: QualityMetrics) -> list[str]:
        """Check if quality metrics meet configured thresholds.

        Args:
            metrics: Quality metrics to check

        Returns:
            List of quality issues (empty if all thresholds met)
        """
        issues = []

        if metrics.faithfulness < self.config.min_faithfulness:
            issues.append(
                f"Low faithfulness: {metrics.faithfulness:.2f} "
                f"< {self.config.min_faithfulness:.2f}",
            )

        if metrics.relevance < self.config.min_relevance:
            issues.append(
                f"Low relevance: {metrics.relevance:.2f} "
                f"< {self.config.min_relevance:.2f}",
            )

        if metrics.confidence < self.config.min_confidence:
            issues.append(
                f"Low confidence: {metrics.confidence:.2f} "
                f"< {self.config.min_confidence:.2f}",
            )

        if self.config.hallucination_detection_enabled and metrics.has_hallucinations:
            issues.append(
                f"Hallucinations detected: {metrics.hallucination_count} claims",
            )

        return issues
