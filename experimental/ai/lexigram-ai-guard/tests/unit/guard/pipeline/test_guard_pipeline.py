"""Unit tests for lexigram-ai-guard pipeline and result types."""

from __future__ import annotations

import pytest

from lexigram.ai.guard.pipeline.guard_pipeline import GuardPipeline
from lexigram.ai.guard.pipeline.result import AggregateGuardResult, GuardAction, GuardCheckResult


from lexigram.result import Result
from lexigram.result import Ok
from lexigram.contracts.ai.exceptions import GuardError

class AlwaysPassInputGuard:
    name = "always_pass_input"

    async def check(self, content: str, *, messages: object = None, metadata: object = None) -> Result[GuardCheckResult, GuardError]:
        return Ok(GuardCheckResult.allow(guard_name=self.name))


class AlwaysBlockInputGuard:
    name = "always_block_input"

    async def check(self, content: str, *, messages: object = None, metadata: object = None) -> Result[GuardCheckResult, GuardError]:
        return Ok(GuardCheckResult.block(guard_name=self.name, reason="blocked by stub"))


class AlwaysRedactInputGuard:
    name = "always_redact_input"

    async def check(self, content: str, *, messages: object = None, metadata: object = None) -> Result[GuardCheckResult, GuardError]:
        return Ok(GuardCheckResult.redact(guard_name=self.name, redacted_content="[REDACTED]", reason="redacted by stub"))


class AlwaysPassOutputGuard:
    name = "always_pass_output"

    async def check(self, content: str, *, original_input: str = "", metadata: object = None) -> Result[GuardCheckResult, GuardError]:
        return Ok(GuardCheckResult.allow(guard_name=self.name))


class AlwaysBlockOutputGuard:
    name = "always_block_output"

    async def check(self, content: str, *, original_input: str = "", metadata: object = None) -> Result[GuardCheckResult, GuardError]:
        return Ok(GuardCheckResult.block(guard_name=self.name, reason="output blocked"))


# ---------------------------------------------------------------------------
# GuardAction
# ---------------------------------------------------------------------------


class TestGuardAction:
    def test_values(self) -> None:
        assert GuardAction.PASS == "pass"
        assert GuardAction.BLOCK == "block"
        assert GuardAction.WARN == "warn"
        assert GuardAction.REDACT == "redact"


# ---------------------------------------------------------------------------
# GuardCheckResult
# ---------------------------------------------------------------------------


class TestGuardCheckResult:
    def test_allow(self) -> None:
        r = GuardCheckResult.allow(guard_name="foo")
        assert r.passed is True
        assert r.action == GuardAction.PASS
        assert r.guard_name == "foo"
        assert r.details == {}
        assert r.redacted_content is None

    def test_block(self) -> None:
        r = GuardCheckResult.block(guard_name="foo", reason="bad content")
        assert r.passed is False
        assert r.action == GuardAction.BLOCK
        assert r.details["reason"] == "bad content"
        assert r.redacted_content is None

    def test_warn(self) -> None:
        r = GuardCheckResult.warn(guard_name="foo", reason="suspicious")
        assert r.passed is True
        assert r.action == GuardAction.WARN
        assert r.details["reason"] == "suspicious"

    def test_redact(self) -> None:
        r = GuardCheckResult.redact(guard_name="foo", redacted_content="[X]", reason="pii")
        assert r.passed is True
        assert r.action == GuardAction.REDACT
        assert r.redacted_content == "[X]"

    def test_frozen(self) -> None:
        r = GuardCheckResult.allow(guard_name="foo")
        with pytest.raises((AttributeError, TypeError)):
            r.passed = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# AggregateGuardResult
# ---------------------------------------------------------------------------


class TestAggregateGuardResult:
    def test_all_pass(self) -> None:
        results = [
            GuardCheckResult.allow("a"),
            GuardCheckResult.allow("b"),
        ]
        agg = AggregateGuardResult.from_results(results, original_content="hello")
        assert agg.passed is True
        assert agg.action == GuardAction.PASS
        assert agg.blocked is False
        assert agg.redacted is False
        assert agg.warned is False
        assert agg.final_content == "hello"

    def test_block_overrides(self) -> None:
        results = [
            GuardCheckResult.allow("a"),
            GuardCheckResult.block("b", reason="bad"),
        ]
        agg = AggregateGuardResult.from_results(results, original_content="hello")
        assert agg.passed is False
        assert agg.action == GuardAction.BLOCK
        assert agg.blocked is True
        assert agg.blocking_result is not None
        assert agg.blocking_result.guard_name == "b"

    def test_redact_propagates_content(self) -> None:
        results = [
            GuardCheckResult.redact("pii", redacted_content="safe content", reason="pii found"),
        ]
        agg = AggregateGuardResult.from_results(results, original_content="original")
        assert agg.passed is True
        assert agg.action == GuardAction.REDACT
        assert agg.redacted is True
        assert agg.final_content == "safe content"

    def test_warn_does_not_fail(self) -> None:
        results = [GuardCheckResult.warn("w", reason="hmm")]
        agg = AggregateGuardResult.from_results(results, original_content="c")
        assert agg.passed is True
        assert agg.warned is True
        assert agg.blocked is False

    def test_block_beats_warn(self) -> None:
        results = [
            GuardCheckResult.warn("w", reason="maybe"),
            GuardCheckResult.block("b", reason="definitely"),
        ]
        agg = AggregateGuardResult.from_results(results, original_content="c")
        assert agg.action == GuardAction.BLOCK

    def test_empty_results(self) -> None:
        agg = AggregateGuardResult.from_results([], original_content="hi")
        assert agg.passed is True
        assert agg.action == GuardAction.PASS


# ---------------------------------------------------------------------------
# GuardPipeline — check_input
# ---------------------------------------------------------------------------


class TestGuardPipelineInput:
    @pytest.mark.asyncio
    async def test_empty_pipeline_passes(self, empty_pipeline: GuardPipeline) -> None:
        result = await empty_pipeline.check_input("hello")
        assert result.unwrap().passed is True
        assert result.unwrap().final_content == "hello"

    @pytest.mark.asyncio
    async def test_pass_guard_passes(self, pass_pipeline: GuardPipeline) -> None:
        result = await pass_pipeline.check_input("hello")
        assert result.unwrap().passed is True

    @pytest.mark.asyncio
    async def test_block_guard_blocks(self) -> None:
        pipeline = GuardPipeline(
            input_guards=[AlwaysPassInputGuard(), AlwaysBlockInputGuard()],
            output_guards=[],
        )
        result = await pipeline.check_input("any content")
        assert result.unwrap().passed is False
        assert result.unwrap().blocked is True

    @pytest.mark.asyncio
    async def test_block_stops_evaluation(self) -> None:
        """GuardProtocol after BLOCK should not be called."""
        called = []

        class TrackingGuard:
            name = "tracker"

            async def check(self, content, *, messages=None, metadata=None):
                called.append(content)
                return Ok(GuardCheckResult.allow(guard_name=self.name))

        pipeline = GuardPipeline(
            input_guards=[AlwaysBlockInputGuard(), TrackingGuard()],
            output_guards=[],
        )
        await pipeline.check_input("test")
        assert called == [], "guard after BLOCK must not run"

    @pytest.mark.asyncio
    async def test_redact_forwards_content(self) -> None:
        """Redacted content must be passed to the next guard in the chain."""
        received = []

        class CapturingGuard:
            name = "capturer"

            async def check(self, content, *, messages=None, metadata=None):
                received.append(content)
                return Ok(GuardCheckResult.allow(guard_name=self.name))

        pipeline = GuardPipeline(
            input_guards=[AlwaysRedactInputGuard(), CapturingGuard()],
            output_guards=[],
        )
        result = await pipeline.check_input("original text")
        assert received == ["[REDACTED]"]
        assert result.unwrap().final_content == "[REDACTED]"

    @pytest.mark.asyncio
    async def test_add_input_guard(self) -> None:
        pipeline = GuardPipeline(input_guards=[], output_guards=[])
        pipeline.add_input_guard(AlwaysPassInputGuard())
        result = await pipeline.check_input("hi")
        assert result.unwrap().passed is True


# ---------------------------------------------------------------------------
# GuardPipeline — check_output
# ---------------------------------------------------------------------------


class TestGuardPipelineOutput:
    @pytest.mark.asyncio
    async def test_empty_pipeline_passes(self, empty_pipeline: GuardPipeline) -> None:
        result = await empty_pipeline.check_output("response", original_input="q")
        assert result.unwrap().passed is True
        assert result.unwrap().final_content == "response"

    @pytest.mark.asyncio
    async def test_block_output_guard(self) -> None:
        pipeline = GuardPipeline(
            input_guards=[],
            output_guards=[AlwaysBlockOutputGuard()],
        )
        result = await pipeline.check_output("bad response", original_input="q")
        assert result.unwrap().passed is False
        assert result.unwrap().blocked is True

    @pytest.mark.asyncio
    async def test_add_output_guard(self) -> None:
        pipeline = GuardPipeline(input_guards=[], output_guards=[])
        pipeline.add_output_guard(AlwaysPassOutputGuard())
        result = await pipeline.check_output("response", original_input="q")
        assert result.unwrap().passed is True


# ---------------------------------------------------------------------------
# Parallel guard evaluation
# ---------------------------------------------------------------------------


class TestGuardPipelineParallel:
    """Tests for parallel guard evaluation via asyncio.gather."""

    @pytest.mark.asyncio
    async def test_parallel_input_all_pass(self) -> None:
        """All input guards pass in parallel mode."""
        pipeline = GuardPipeline(
            input_guards=[AlwaysPassInputGuard(), AlwaysPassInputGuard()],
            output_guards=[],
        )
        result = await pipeline.check_input("hello", parallel=True)
        assert result.is_ok()
        assert result.unwrap().passed is True

    @pytest.mark.asyncio
    async def test_parallel_input_block(self) -> None:
        """A blocking guard in parallel mode stops with block result."""
        pipeline = GuardPipeline(
            input_guards=[AlwaysPassInputGuard(), AlwaysBlockInputGuard()],
            output_guards=[],
        )
        result = await pipeline.check_input("hello", parallel=True)
        assert result.is_ok()
        assert result.unwrap().blocked is True

    @pytest.mark.asyncio
    async def test_parallel_output_all_pass(self) -> None:
        """All output guards pass in parallel mode."""
        pipeline = GuardPipeline(
            input_guards=[],
            output_guards=[AlwaysPassOutputGuard(), AlwaysPassOutputGuard()],
        )
        result = await pipeline.check_output("response", original_input="q", parallel=True)
        assert result.is_ok()
        assert result.unwrap().passed is True

    @pytest.mark.asyncio
    async def test_parallel_output_block(self) -> None:
        """A blocking output guard in parallel mode returns block result."""
        pipeline = GuardPipeline(
            input_guards=[],
            output_guards=[AlwaysPassOutputGuard(), AlwaysBlockOutputGuard()],
        )
        result = await pipeline.check_output("response", original_input="q", parallel=True)
        assert result.is_ok()
        assert result.unwrap().blocked is True


# ---------------------------------------------------------------------------
# Sensitivity configuration
# ---------------------------------------------------------------------------


class TestGuardConfigSensitivity:
    """Tests for configurable sensitivity levels."""

    def test_default_sensitivity_is_medium(self) -> None:
        from lexigram.ai.guard.config import GuardConfig
        config = GuardConfig()
        assert config.sensitivity_level == "medium"

    def test_custom_sensitivity_high(self) -> None:
        from lexigram.ai.guard.config import GuardConfig
        config = GuardConfig(sensitivity_level="high")
        assert config.sensitivity_level == "high"

    def test_custom_sensitivity_low(self) -> None:
        from lexigram.ai.guard.config import GuardConfig
        config = GuardConfig(sensitivity_level="low")
        assert config.sensitivity_level == "low"

    def test_parallel_execution_default_off(self) -> None:
        from lexigram.ai.guard.config import GuardConfig
        config = GuardConfig()
        assert config.parallel_execution is False

    def test_parallel_execution_enabled(self) -> None:
        from lexigram.ai.guard.config import GuardConfig
        config = GuardConfig(parallel_execution=True)
        assert config.parallel_execution is True
