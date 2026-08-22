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




class TestPipeline:
    """Test Pipeline functionality."""

    def test_pipeline_creation(self):
        """Test creating a pipeline."""
        steps = [
            FunctionStep("step1", lambda ctx: Ok("result1")),
            FunctionStep("step2", lambda ctx: Ok("result2")),
        ]

        pipeline = Pipeline("test_pipeline", steps)
        assert pipeline.name == "test_pipeline"
        assert pipeline.steps == steps

    def test_pipeline_duplicate_step_names(self):
        """Test pipeline validation with duplicate step names."""
        steps = [
            FunctionStep("step1", lambda ctx: Ok("result1")),
            FunctionStep("step1", lambda ctx: Ok("result2")),
        ]

        with pytest.raises(ValueError, match="Duplicate step names found"):
            Pipeline("test_pipeline", steps)

    def test_pipeline_missing_dependency(self):
        """Test pipeline validation with missing dependency."""
        steps = [
            FunctionStep(
                "step1",
                lambda ctx: Ok("result1"),
                dependencies=["missing_dep"],
            ),
        ]

        with pytest.raises(ValueError, match="depends on unknown step"):
            Pipeline("test_pipeline", steps)

    def test_pipeline_circular_dependency(self):
        """Test pipeline validation with circular dependency."""
        steps = [
            FunctionStep("step1", lambda ctx: Ok("result1"), dependencies=["step2"]),
            FunctionStep("step2", lambda ctx: Ok("result2"), dependencies=["step1"]),
        ]

        with pytest.raises(ValueError, match="Circular dependency detected"):
            Pipeline("test_pipeline", steps)

    @pytest.mark.asyncio
    async def test_execute_simple_pipeline(self):
        """Test executing a simple pipeline."""
        steps = [
            FunctionStep("step1", lambda ctx: Ok("result1")),
            FunctionStep("step2", lambda ctx: Ok("result2")),
        ]

        pipeline = Pipeline("test_pipeline", steps)
        result = await pipeline.execute()

        assert result.is_ok()
        context = result.unwrap()
        assert context.pipeline_name == "test_pipeline"
        assert context.get_step_result("step1") == "result1"
        assert context.get_step_result("step2") == "result2"
        assert context.start_time is not None
        assert context.end_time is not None

    @pytest.mark.asyncio
    async def test_execute_pipeline_with_dependencies(self):
        """Test executing pipeline with dependencies."""

        async def step2_func(ctx):
            step1_result = ctx.get_step_result("step1")
            return Ok(f"processed_{step1_result}")

        steps = [
            FunctionStep("step1", lambda ctx: Ok("result1")),
            FunctionStep("step2", step2_func, dependencies=["step1"]),
        ]

        pipeline = Pipeline("test_pipeline", steps)
        result = await pipeline.execute()

        assert result.is_ok()
        context = result.unwrap()
        assert context.get_step_result("step1") == "result1"
        assert context.get_step_result("step2") == "processed_result1"

    @pytest.mark.asyncio
    async def test_execute_pipeline_with_failure_fail_fast(self):
        """Test executing pipeline with step failure (fail fast)."""

        async def failing_func(ctx):
            raise ValueError("step failed")

        steps = [
            FunctionStep("step1", lambda ctx: Ok("result1")),
            FunctionStep("step2", failing_func),
            FunctionStep("step3", lambda ctx: Ok("result3")),
        ]

        pipeline = Pipeline("test_pipeline", steps)
        result = await pipeline.execute(fail_fast=True)

        assert result.is_err()
        assert isinstance(result.unwrap_err(), PipelineExecutionError)

    @pytest.mark.asyncio
    async def test_execute_pipeline_with_failure_no_fail_fast(self):
        """Test executing pipeline with step failure (no fail fast)."""

        async def failing_func(ctx):
            raise ValueError("step failed")

        steps = [
            FunctionStep("step1", lambda ctx: Ok("result1")),
            FunctionStep("step2", failing_func),
            FunctionStep("step3", lambda ctx: Ok("result3")),
        ]

        pipeline = Pipeline("test_pipeline", steps)
        result = await pipeline.execute(fail_fast=False)

        assert result.is_err()
        assert isinstance(result.unwrap_err(), PipelineExecutionError)

    @pytest.mark.asyncio
    async def test_execute_pipeline_with_skip(self):
        """Test executing pipeline with skipped steps."""

        async def skip_func(ctx):
            return Ok(True)

        steps = [
            FunctionStep("step1", lambda ctx: Ok("result1")),
            FunctionStep("step2", lambda ctx: Ok("result2"), skip_condition=skip_func),
            FunctionStep("step3", lambda ctx: Ok("result3")),
        ]

        pipeline = Pipeline("test_pipeline", steps)
        result = await pipeline.execute()

        assert result.is_ok()
        context = result.unwrap()
        assert context.get_step_result("step1") == "result1"
        assert context.get_step_result("step2") is None  # Skipped
        assert context.get_step_result("step3") == "result3"

    @pytest.mark.asyncio
    async def test_execute_pipeline_with_custom_context(self):
        """Test executing pipeline with custom initial context."""
        initial_context = PipelineContext("custom_pipeline")
        initial_context.add_metadata("custom_key", "custom_value")

        steps = [FunctionStep("step1", lambda ctx: Ok("result1"))]

        pipeline = Pipeline("test_pipeline", steps)
        result = await pipeline.execute(initial_context)

        assert result.is_ok()
        context = result.unwrap()
        assert context.pipeline_name == "custom_pipeline"  # Uses initial context
        assert context.get_metadata("custom_key") == "custom_value"

    @pytest.mark.asyncio
    async def test_step_timeout_causes_failure(self):
        """A step that exceeds its timeout should fail with TimeoutError."""

        async def slow(ctx):
            await asyncio.sleep(0.2)
            return Ok("late")

        steps = [FunctionStep("slow", slow, timeout=0.1), FunctionStep("next", lambda ctx: Ok("ok"))]
        pipeline = Pipeline("timed", steps)
        result = await pipeline.execute()

        assert result.is_err()
        err = result.unwrap_err()
        assert isinstance(err, PipelineExecutionError)
        # underlying exception should be a TimeoutError
        assert isinstance(err.error, TimeoutError)

        # pipeline should not execute the second step because fail_fast default
        # run it again with fail_fast=False to confirm
        pipeline2 = Pipeline("timed", steps)
        result2 = await pipeline2.execute(fail_fast=False)
        assert result2.is_err()
        assert isinstance(result2.unwrap_err(), PipelineExecutionError)


class TestUtilityFunctions:
    """Test utility functions."""

    def test_step_function(self):
        """Test step utility function."""

        async def test_func(ctx):
            return Ok("result")

        step_obj = step("test_step", test_func, ["dep1", "dep2"])

        assert isinstance(step_obj, FunctionStep)
        assert step_obj.name == "test_step"
        assert step_obj.dependencies == ["dep1", "dep2"]

    def test_conditional_function(self):
        """Test conditional utility function."""

        async def condition(ctx):
            return Ok(True)

        true_step = FunctionStep("true", lambda ctx: Ok("true"))
        false_step = FunctionStep("false", lambda ctx: Ok("false"))

        conditional_step = conditional(
            "conditional",
            condition,
            true_step,
            false_step,
            ["dep1"],
        )

        assert isinstance(conditional_step, ConditionalStep)
        assert conditional_step.name == "conditional"
        assert conditional_step.dependencies == ["dep1"]

    def test_parallel_function(self):
        """Test parallel utility function."""
        steps_list = [FunctionStep("step1", lambda ctx: Ok("result1"))]

        parallel_step = parallel("parallel", steps_list, ["dep1"], fail_fast=False)

        assert isinstance(parallel_step, ParallelStep)
        assert parallel_step.name == "parallel"
        assert parallel_step.fail_fast is False


    def test_pipeline_step_decorator(self):
        """Test pipeline_step decorator."""

        @pipeline_step(dependencies=["dep1"])
        async def my_step(ctx):
            return Ok("result")

        assert isinstance(my_step, FunctionStep)
        assert my_step.name == "my_step"
        assert my_step.dependencies == ["dep1"]
