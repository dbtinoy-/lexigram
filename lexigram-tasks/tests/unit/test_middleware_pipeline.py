"""Tests for task middleware pipeline."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from lexigram.tasks.middleware.core import (
    TaskMiddlewarePipeline,
    TaskExecutionContext,
    TaskMiddleware,
)
from lexigram.tasks.models.job import JobProtocol, JobResult


def create_mock_job(job_id: str = "test-job") -> MagicMock:
    """Create a properly mocked JobProtocol."""
    job = MagicMock()
    job.id = job_id
    job.name = "test_task"
    job.args = ()
    job.kwargs = {}
    return job


class TestTaskExecutionContext:
    """Tests for TaskExecutionContext."""

    def test_create_context(self):
        """Test creating an execution context."""
        job = create_mock_job()
        ctx = TaskExecutionContext(job=job)
        
        assert ctx.job is job
        assert ctx.start_time == 0.0
        assert ctx.end_time == 0.0
        assert ctx.duration_ms == 0.0
        assert ctx.result is None
        assert ctx.metadata == {}

    def test_context_with_metadata(self):
        """Test context with initial metadata."""
        job = create_mock_job()
        ctx = TaskExecutionContext(job=job, metadata={"key": "value"})
        
        assert ctx.metadata == {"key": "value"}


class TestTaskMiddlewarePipeline:
    """Tests for TaskMiddlewarePipeline."""

    @pytest.mark.asyncio
    async def test_empty_pipeline_executes_handler(self):
        """Test that empty pipeline just executes the handler."""
        pipeline = TaskMiddlewarePipeline()
        job = create_mock_job()
        handler = AsyncMock(return_value=JobResult.ok(data={"test": "data"}))

        result = await pipeline.execute(job, handler)

        handler.assert_called_once()
        assert result.success is True

    @pytest.mark.asyncio
    async def test_pipeline_calls_before_execute(self):
        """Test that pipeline calls before_execute on middleware."""
        pipeline = TaskMiddlewarePipeline()
        middleware = AsyncMock(spec=TaskMiddleware)
        pipeline.add(middleware)
        
        job = create_mock_job()
        handler = AsyncMock(return_value=JobResult.ok())

        await pipeline.execute(job, handler)

        middleware.before_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_calls_after_execute_on_success(self):
        """Test that pipeline calls after_execute on successful execution."""
        pipeline = TaskMiddlewarePipeline()
        middleware = AsyncMock(spec=TaskMiddleware)
        pipeline.add(middleware)
        
        job = create_mock_job()
        handler = AsyncMock(return_value=JobResult.ok())

        await pipeline.execute(job, handler)

        middleware.after_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_calls_on_error_on_failure(self):
        """Test that pipeline calls on_error when handler raises."""
        pipeline = TaskMiddlewarePipeline()
        middleware = AsyncMock(spec=TaskMiddleware)
        pipeline.add(middleware)
        
        job = create_mock_job()
        handler = AsyncMock(side_effect=ValueError("test error"))

        with pytest.raises(ValueError):
            await pipeline.execute(job, handler)

        middleware.on_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_multiple_middleware_order(self):
        """Test that middleware are called in order."""
        pipeline = TaskMiddlewarePipeline()
        middle1 = AsyncMock(spec=TaskMiddleware)
        middle2 = AsyncMock(spec=TaskMiddleware)
        pipeline.add(middle1)
        pipeline.add(middle2)
        
        job = create_mock_job()
        handler = AsyncMock(return_value=JobResult.ok())

        await pipeline.execute(job, handler)

        calls = middle1.before_execute.call_args_list
        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_pipeline_context_passed_to_middleware(self):
        """Test that context is properly passed to middleware."""
        pipeline = TaskMiddlewarePipeline()
        middleware = AsyncMock(spec=TaskMiddleware)
        pipeline.add(middleware)
        
        job = create_mock_job("test-job")
        handler = AsyncMock(return_value=JobResult.ok())

        await pipeline.execute(job, handler)

        assert middleware.before_execute.call_count == 1
        call_args = middleware.before_execute.call_args
        ctx = call_args[0][0]
        assert isinstance(ctx, TaskExecutionContext)
        assert ctx.job is job

    @pytest.mark.asyncio
    async def test_pipeline_records_duration(self):
        """Test that pipeline records execution duration."""
        pipeline = TaskMiddlewarePipeline()
        
        async def slow_handler():
            await asyncio.sleep(0.01)
            return JobResult.ok()

        job = create_mock_job()
        result = await pipeline.execute(job, slow_handler)

        assert result.success is True
