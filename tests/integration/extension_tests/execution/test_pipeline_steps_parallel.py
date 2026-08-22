"""
Tests for pipeline execution functionality.
"""

import asyncio

import pytest

from lexigram.contracts.exceptions import PipelineExecutionError
from lexigram.workflow.pipeline import (
    ConditionalStep,
    FunctionStep,
    ParallelStep,
    Pipeline,
    PipelineContext,
    PipelineStep,
    StepExecutionResult,
    StepStatus,
    conditional,
    parallel,
    pipeline_step,
    step,
)
from lexigram.result import Err, Ok




class TestParallelStep:
    """Test ParallelStep functionality."""

    def test_parallel_step_creation(self):
        """Test creating a parallel step."""
        steps = [
            FunctionStep("step1", lambda ctx: Ok("result1")),
            FunctionStep("step2", lambda ctx: Ok("result2")),
        ]

        step = ParallelStep("parallel", steps)
        assert step.name == "parallel"
        assert step.steps == steps
        assert step.fail_fast is True

    def test_parallel_step_with_options(self):
        """Test creating parallel step with options."""
        steps = [FunctionStep("step1", lambda ctx: Ok("result1"))]

        step = ParallelStep("parallel", steps, dependencies=["dep1"], fail_fast=False)
        assert step.name == "parallel"
        assert step.dependencies == ["dep1"]
        assert step.fail_fast is False

    @pytest.mark.asyncio
    async def test_execute_all_success(self):
        """Test executing parallel steps where all succeed."""
        step1 = FunctionStep("step1", lambda ctx: Ok("result1"))
        step2 = FunctionStep("step2", lambda ctx: Ok("result2"))
        step = ParallelStep("parallel", [step1, step2])
        context = PipelineContext("test_pipeline")

        result = await step.execute(context)
        assert result.is_ok()
        assert result.unwrap() == ["result1", "result2"]

    @pytest.mark.asyncio
    async def test_execute_with_failure_fail_fast(self):
        """Test executing parallel steps with failure (fail fast)."""

        async def failing_func(ctx):
            raise ValueError("step failed")

        step1 = FunctionStep("step1", lambda ctx: Ok("result1"))
        step2 = FunctionStep("step2", failing_func)
        step3 = FunctionStep("step3", lambda ctx: Ok("result3"))

        step = ParallelStep("parallel", [step1, step2, step3], fail_fast=True)
        context = PipelineContext("test_pipeline")

        result = await step.execute(context)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), PipelineExecutionError)

    @pytest.mark.asyncio
    async def test_execute_with_failure_no_fail_fast(self):
        """Test executing parallel steps with failure (no fail fast)."""

        async def failing_func(ctx):
            raise ValueError("step failed")

        step1 = FunctionStep("step1", lambda ctx: Ok("result1"))
        step2 = FunctionStep("step2", failing_func)
        step3 = FunctionStep("step3", lambda ctx: Ok("result3"))

        step = ParallelStep("parallel", [step1, step2, step3], fail_fast=False)
        context = PipelineContext("test_pipeline")

        result = await step.execute(context)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), PipelineExecutionError)


