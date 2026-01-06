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


class TestPipelineContext:
    """Test PipelineContext functionality."""

    def test_context_creation(self):
        """Test creating a pipeline context."""
        context = PipelineContext("test_pipeline")

        assert context.pipeline_name == "test_pipeline"
        assert context.step_results == {}
        assert context.metadata == {}
        assert context.start_time is None
        assert context.end_time is None

    def test_context_with_initial_data(self):
        """Test creating context with initial data."""
        initial_results = {"step1": "result1"}
        initial_metadata = {"key": "value"}

        context = PipelineContext(
            "test_pipeline",
            step_results=initial_results,
            metadata=initial_metadata,
        )

        assert context.step_results == initial_results
        assert context.metadata == initial_metadata

    def test_get_step_result(self):
        """Test getting step results."""
        context = PipelineContext("test_pipeline")
        context.set_step_result("step1", "result1")

        assert context.get_step_result("step1") == "result1"
        assert context.get_step_result("nonexistent") is None
        assert context.get_step_result("nonexistent", "default") == "default"

    def test_set_step_result(self):
        """Test setting step results."""
        context = PipelineContext("test_pipeline")

        context.set_step_result("step1", "result1")
        context.set_step_result("step2", {"key": "value"})

        assert context.step_results["step1"] == "result1"
        assert context.step_results["step2"] == {"key": "value"}

    def test_metadata_operations(self):
        """Test metadata operations."""
        context = PipelineContext("test_pipeline")

        context.add_metadata("key1", "value1")
        context.add_metadata("key2", 42)

        assert context.get_metadata("key1") == "value1"
        assert context.get_metadata("key2") == 42
        assert context.get_metadata("nonexistent") is None
        assert context.get_metadata("nonexistent", "default") == "default"


class TestStepExecutionResult:
    """Test StepExecutionResult functionality."""

    def test_result_creation_minimal(self):
        """Test creating a minimal step execution result."""
        result = StepExecutionResult("test_step", StepStatus.PENDING)

        assert result.step_name == "test_step"
        assert result.status == StepStatus.PENDING
        assert result.result is None
        assert result.error is None
        assert result.duration is None
        assert result.skipped_reason is None

    def test_result_creation_complete(self):
        """Test creating a complete step execution result."""
        error = ValueError("test error")

        result = StepExecutionResult(
            step_name="test_step",
            status=StepStatus.FAILED,
            result="some_result",
            error=error,
            duration=1.5,
            skipped_reason="condition not met",
        )

        assert result.step_name == "test_step"
        assert result.status == StepStatus.FAILED
        assert result.result == "some_result"
        assert result.error == error
        assert result.duration == 1.5
        assert result.skipped_reason == "condition not met"


class TestPipelineStep:
    """Test PipelineStep abstract base class."""

    def test_step_creation(self):
        """Test creating a pipeline step."""

        # Create a concrete implementation for testing
        class ConcreteStep(PipelineStep):
            async def execute(self, context):
                return Ok("test_result")

        step = ConcreteStep("test_step")
        assert step.name == "test_step"
        assert step.dependencies == []

    def test_step_with_dependencies(self):
        """Test creating a step with dependencies."""

        # Create a concrete implementation for testing
        class ConcreteStep(PipelineStep):
            async def execute(self, context):
                return Ok("test_result")

        step = ConcreteStep("test_step", ["dep1", "dep2"])
        assert step.name == "test_step"
        assert step.dependencies == ["dep1", "dep2"]

    @pytest.mark.asyncio
    async def test_should_skip_default(self):
        """Test default should_skip implementation."""

        # Create a concrete implementation for testing
        class ConcreteStep(PipelineStep):
            async def execute(self, context):
                return Ok("test_result")

        step = ConcreteStep("test_step")
        context = PipelineContext("test_pipeline")

        result = await step.should_skip(context)
        assert result == Ok(False)

    @pytest.mark.asyncio
    async def test_on_error_default(self):
        """Test default on_error implementation."""

        # Create a concrete implementation for testing
        class ConcreteStep(PipelineStep):
            async def execute(self, context):
                return Ok("test_result")

        step = ConcreteStep("test_step")
        context = PipelineContext("test_pipeline")
        error = ValueError("test error")

        with pytest.raises(ValueError):
            await step.on_error(context, error)

    @pytest.mark.asyncio
    async def test_cleanup_default(self):
        """Test default cleanup implementation."""

        # Create a concrete implementation for testing
        class ConcreteStep(PipelineStep):
            async def execute(self, context):
                return Ok("test_result")

        step = ConcreteStep("test_step")
        context = PipelineContext("test_pipeline")

        result = await step.cleanup(context)
        assert result is not None
        assert result.is_ok()


class TestFunctionStep:
    """Test FunctionStep functionality."""

    def test_function_step_creation(self):
        """Test creating a function step."""

        async def test_func(context):
            return Ok("result")

        step = FunctionStep("test_step", test_func)
        assert step.name == "test_step"
        assert step.func == test_func
        assert step.skip_condition is None
        assert step.error_handler is None
        assert step.cleanup_func is None

    def test_function_step_with_options(self):
        """Test creating a function step with all options."""

        async def test_func(context):
            return Ok("result")

        async def skip_func(context):
            return Ok(False)

        async def error_func(context, error):
            return Ok("handled")

        async def cleanup_func(context):
            return Ok(None)

        step = FunctionStep(
            "test_step",
            test_func,
            dependencies=["dep1"],
            skip_condition=skip_func,
            error_handler=error_func,
            cleanup_func=cleanup_func,
        )

        assert step.name == "test_step"
        assert step.dependencies == ["dep1"]
        assert step.skip_condition == skip_func
        assert step.error_handler == error_func
        assert step.cleanup_func == cleanup_func

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful function execution."""

        async def test_func(context):
            return Ok("success_result")

        step = FunctionStep("test_step", test_func)
        context = PipelineContext("test_pipeline")

        result = await step.execute(context)
        assert result.is_ok()
        assert result.unwrap() == "success_result"

    @pytest.mark.asyncio
    async def test_execute_error(self):
        """Test function execution with error."""

        async def test_func(context):
            raise ValueError("test error")

        step = FunctionStep("test_step", test_func)
        context = PipelineContext("test_pipeline")

        result = await step.execute(context)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ValueError)

    @pytest.mark.asyncio
    async def test_execute_sync_function(self):
        """Test executing a synchronous function."""

        def test_func(context):
            return Ok("sync_result")

        step = FunctionStep("test_step", test_func)
        context = PipelineContext("test_pipeline")

        result = await step.execute(context)
        assert result.is_ok()
        assert result.unwrap() == "sync_result"

    @pytest.mark.asyncio
    async def test_should_skip_with_condition(self):
        """Test should_skip with custom condition."""

        async def skip_func(context):
            return Ok(True)

        step = FunctionStep("test_step", lambda ctx: Ok(None), skip_condition=skip_func)
        context = PipelineContext("test_pipeline")

        result = await step.should_skip(context)
        assert result.is_ok()
        assert result.unwrap() is True

    @pytest.mark.asyncio
    async def test_should_skip_condition_error(self):
        """Test should_skip when condition raises error."""

        async def skip_func(context):
            raise ValueError("skip error")

        step = FunctionStep("test_step", lambda ctx: Ok(None), skip_condition=skip_func)
        context = PipelineContext("test_pipeline")

        result = await step.should_skip(context)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ValueError)

    @pytest.mark.asyncio
    async def test_on_error_with_handler(self):
        """Test on_error with custom handler."""

        async def error_func(context, error):
            return Ok("handled")

        step = FunctionStep("test_step", lambda ctx: Ok(None), error_handler=error_func)
        context = PipelineContext("test_pipeline")
        error = ValueError("test error")

        result = await step.on_error(context, error)
        assert result.is_ok()
        assert result.unwrap() == "handled"

    @pytest.mark.asyncio
    async def test_cleanup_with_function(self):
        """Test cleanup with custom function."""

        async def cleanup_func(context):
            return Ok(None)

        step = FunctionStep(
            "test_step",
            lambda ctx: Ok(None),
            cleanup_func=cleanup_func,
        )
        context = PipelineContext("test_pipeline")

        result = await step.cleanup(context)
        assert result.is_ok()
        assert result.unwrap() is None


class TestConditionalStep:
    """Test ConditionalStep functionality."""

    def test_conditional_step_creation(self):
        """Test creating a conditional step."""

        async def condition(context):
            return Ok(True)

        true_step = FunctionStep("true_step", lambda ctx: Ok("true"))
        false_step = FunctionStep("false_step", lambda ctx: Ok("false"))

        step = ConditionalStep("conditional", condition, true_step, false_step)
        assert step.name == "conditional"
        assert step.condition == condition
        assert step.true_step == true_step
        assert step.false_step == false_step

    def test_conditional_step_without_false_step(self):
        """Test creating conditional step without false step."""

        async def condition(context):
            return Ok(False)

        true_step = FunctionStep("true_step", lambda ctx: Ok("true"))

        step = ConditionalStep("conditional", condition, true_step)
        assert step.false_step is None

    @pytest.mark.asyncio
    async def test_execute_true_condition(self):
        """Test executing when condition is true."""

        async def condition(context):
            return Ok(True)

        true_step = FunctionStep("true_step", lambda ctx: Ok("true_result"))
        step = ConditionalStep("conditional", condition, true_step)
        context = PipelineContext("test_pipeline")

        result = await step.execute(context)
        assert result.is_ok()
        assert result.unwrap() == "true_result"

    @pytest.mark.asyncio
    async def test_execute_false_condition_with_false_step(self):
        """Test executing when condition is false with false step."""

        async def condition(context):
            return Ok(False)

        true_step = FunctionStep("true_step", lambda ctx: Ok("true"))
        false_step = FunctionStep("false_step", lambda ctx: Ok("false_result"))

        step = ConditionalStep("conditional", condition, true_step, false_step)
        context = PipelineContext("test_pipeline")

        result = await step.execute(context)
        assert result.is_ok()
        assert result.unwrap() == "false_result"

    @pytest.mark.asyncio
    async def test_execute_false_condition_without_false_step(self):
        """Test executing when condition is false without false step."""

        async def condition(context):
            return Ok(False)

        true_step = FunctionStep("true_step", lambda ctx: Ok("true"))
        step = ConditionalStep("conditional", condition, true_step)
        context = PipelineContext("test_pipeline")

        result = await step.execute(context)
        assert result.is_ok()
        assert result.unwrap() is None

    @pytest.mark.asyncio
    async def test_execute_condition_error(self):
        """Test executing when condition raises error."""

        async def condition(context):
            raise ValueError("condition error")

        true_step = FunctionStep("true_step", lambda ctx: Ok("true"))
        step = ConditionalStep("conditional", condition, true_step)
        context = PipelineContext("test_pipeline")

        result = await step.execute(context)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ValueError)

    @pytest.mark.asyncio
    async def test_execute_condition_returns_error(self):
        """Test executing when condition returns error."""

        async def condition(context):
            return Err(ValueError("condition failed"))

        true_step = FunctionStep("true_step", lambda ctx: Ok("true"))
        step = ConditionalStep("conditional", condition, true_step)
        context = PipelineContext("test_pipeline")

        result = await step.execute(context)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ValueError)

    @pytest.mark.asyncio
    async def test_should_skip(self):
        """Test that conditional steps are never skipped."""

        async def condition(context):
            return Ok(True)

        true_step = FunctionStep("true_step", lambda ctx: Ok("true"))
        step = ConditionalStep("conditional", condition, true_step)
        context = PipelineContext("test_pipeline")

        result = await step.should_skip(context)
        assert result.is_ok()
        assert result.unwrap() is False


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
