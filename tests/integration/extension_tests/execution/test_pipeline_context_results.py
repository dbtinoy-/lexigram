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


