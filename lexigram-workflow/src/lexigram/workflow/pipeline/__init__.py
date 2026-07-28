"""Pipeline pattern implementation for lexigram-workflow.

The Pipeline pattern provides a declarative way to compose complex business
workflows with proper error handling, context propagation, and async execution.
"""

from __future__ import annotations

from lexigram.primitives.pipeline import (
    PipelineContext,
    StepExecutionResult,
    StepStatus,
)
from lexigram.workflow.pipeline.decorators import (
    conditional,
    parallel,
    pipeline_step,
    step,
)
from lexigram.workflow.pipeline.executor import Pipeline
from lexigram.workflow.pipeline.steps import (
    ConditionalStep,
    FunctionStep,
    ParallelStep,
    PipelineStep,
)

__all__ = [
    "ConditionalStep",
    "FunctionStep",
    "ParallelStep",
    "Pipeline",
    "PipelineContext",
    "PipelineStep",
    "StepExecutionResult",
    "StepStatus",
    "conditional",
    "parallel",
    "pipeline_step",
    "step",
]
