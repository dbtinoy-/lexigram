"""Unit tests for guard pipeline error handling."""

from __future__ import annotations

import pytest

from lexigram.ai.guard.pipeline.guard_pipeline import GuardPipeline
from lexigram.ai.guard.pipeline.result import GuardCheckResult
from lexigram.contracts.ai.exceptions import GuardError
from lexigram.result import Err, Ok, Result


class GuardReturnsErr:
    """Guard that returns Err result."""

    name = "guard_returns_err"

    async def check(
        self,
        content: str,
        *,
        messages: object = None,
        metadata: object = None,
    ) -> Result[GuardCheckResult, GuardError]:
        return Err(GuardError("guard failed"))


class GuardRaisesException:
    """Guard that raises an exception."""

    name = "guard_raises_exception"

    async def check(
        self,
        content: str,
        *,
        messages: object = None,
        metadata: object = None,
    ) -> Result[GuardCheckResult, GuardError]:
        raise RuntimeError("guard exploded")


class GuardRaisesExceptionOutput:
    """Output guard that raises an exception."""

    name = "guard_raises_exception_output"

    async def check(
        self,
        content: str,
        *,
        original_input: str = "",
        metadata: object = None,
    ) -> Result[GuardCheckResult, GuardError]:
        raise RuntimeError("guard exploded")


class GuardReturnsErrOutput:
    """Output guard that returns Err result."""

    name = "guard_returns_err_output"

    async def check(
        self,
        content: str,
        *,
        original_input: str = "",
        metadata: object = None,
    ) -> Result[GuardCheckResult, GuardError]:
        return Err(GuardError("guard failed"))


class GuardPasses:
    """Guard that passes content."""

    name = "guard_passes"

    async def check(
        self,
        content: str,
        *,
        messages: object = None,
        metadata: object = None,
    ) -> Result[GuardCheckResult, GuardError]:
        return Ok(GuardCheckResult.allow(guard_name=self.name))


# ---------------------------------------------------------------------------
# TestGuardPipelineErrorHandling
# ---------------------------------------------------------------------------


class TestGuardPipelineErrorHandling:
    """Tests for error propagation in GuardPipeline."""

    @pytest.mark.asyncio
    async def test_guard_returns_err_propagates(self) -> None:
        """When guard returns Err, pipeline should propagate it."""
        pipeline = GuardPipeline(
            input_guards=[GuardReturnsErr()],
            output_guards=[],
        )
        result = await pipeline.check_input("test content")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), GuardError)

    @pytest.mark.asyncio
    async def test_parallel_guard_exception_returns_err(self) -> None:
        """When guard raises exception in parallel mode, pipeline returns Err."""
        pipeline = GuardPipeline(
            input_guards=[GuardRaisesException()],
            output_guards=[],
        )
        result = await pipeline.check_input("test content", parallel=True)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), GuardError)

    @pytest.mark.asyncio
    async def test_guard_exception_returns_err(self) -> None:
        """When guard raises exception in non-parallel mode, exception propagates."""
        pipeline = GuardPipeline(
            input_guards=[GuardRaisesException()],
            output_guards=[],
        )
        with pytest.raises(RuntimeError, match="guard exploded"):
            await pipeline.check_input("test content")

    @pytest.mark.asyncio
    async def test_parallel_guard_returns_err(self) -> None:
        """When guard returns Err in parallel mode, pipeline propagates it."""
        pipeline = GuardPipeline(
            input_guards=[GuardReturnsErr()],
            output_guards=[],
        )
        result = await pipeline.check_input("test content", parallel=True)
        assert result.is_err()

    @pytest.mark.asyncio
    async def test_first_err_stops_evaluation(self) -> None:
        """First Err stops guard chain evaluation."""
        call_order = []

        class FirstGuard:
            name = "first_guard"

            async def check(self, content, *, messages=None, metadata=None):
                call_order.append("first")
                return Err(GuardError("first failed"))

        class SecondGuard:
            name = "second_guard"

            async def check(self, content, *, messages=None, metadata=None):
                call_order.append("second")
                return Ok(GuardCheckResult.allow(guard_name=self.name))

        pipeline = GuardPipeline(
            input_guards=[FirstGuard(), SecondGuard()],
            output_guards=[],
        )
        result = await pipeline.check_input("test")
        assert result.is_err()
        assert call_order == ["first"]

    @pytest.mark.asyncio
    async def test_output_guard_err_propagates(self) -> None:
        """Output guard returning Err should propagate."""
        pipeline = GuardPipeline(
            input_guards=[],
            output_guards=[GuardReturnsErrOutput()],
        )
        result = await pipeline.check_output("response", original_input="query")
        assert result.is_err()

    @pytest.mark.asyncio
    async def test_output_guard_exception_propagates(self) -> None:
        """Output guard raising exception in non-parallel mode propagates."""
        pipeline = GuardPipeline(
            input_guards=[],
            output_guards=[GuardRaisesExceptionOutput()],
        )
        with pytest.raises(RuntimeError, match="guard exploded"):
            await pipeline.check_output("response", original_input="query")
