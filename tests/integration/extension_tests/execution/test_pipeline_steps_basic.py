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


