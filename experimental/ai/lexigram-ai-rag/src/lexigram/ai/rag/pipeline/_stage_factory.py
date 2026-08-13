"""Factory utilities for constructing configured RAG pipeline stages."""

from __future__ import annotations

from lexigram.ai.rag.config import PipelineConfig, PipelineStageType
from lexigram.ai.rag.pipeline.base import PipelineStageProtocol


def build_pipeline_stages(config: PipelineConfig) -> list[PipelineStageProtocol]:
    """Build pipeline stages based on the provided pipeline config."""
    from lexigram.ai.rag.pipeline.stages import (
        QualityAssuranceStage,
        RetrievalStage,
        SynthesisStage,
    )

    stages: list[PipelineStageProtocol] = []

    for stage_type in config.stages:
        if stage_type == PipelineStageType.RETRIEVAL and config.retrieval.enabled:
            stages.append(RetrievalStage(config=config.retrieval))
        elif stage_type == PipelineStageType.SYNTHESIS and config.synthesis.enabled:
            stages.append(SynthesisStage(config=config.synthesis))
        elif (
            stage_type == PipelineStageType.QUALITY_ASSURANCE
            and config.quality_assurance.enabled
        ):
            stages.append(QualityAssuranceStage(config=config.quality_assurance))

    return stages
