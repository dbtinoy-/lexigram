from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from lexigram.ai.prompt.optimization.optimizer import PromptOptimizer
from lexigram.ai.prompt.optimization.types import (
    Example,
    OptimizedPrompt,
)
from lexigram.result import Ok


@dataclass
class _FakeCompletion:
    content: str
    model: str = "fake-model"


class _FakeLLM:
    def __init__(self, response: str = "predicted") -> None:
        self._response = response
        self.call_count = 0

    async def complete(self, messages: Any, **kwargs: Any) -> Ok[_FakeCompletion]:
        self.call_count += 1
        return Ok(_FakeCompletion(content=self._response))

    async def stream_chat(self, messages: Any, **kwargs: Any) -> Ok[Any]:
        return Ok(None)

    async def health_check(self, timeout: float = 5.0) -> Any:
        from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
        return HealthCheckResult(component="fake-llm", status=HealthStatus.HEALTHY)

    async def close(self) -> None:
        pass


def _always_one(_prediction: str, _expected: str) -> float:
    return 1.0


def _always_zero(_prediction: str, _expected: str) -> float:
    return 0.0


def _make_examples(n: int) -> list[Example]:
    return [
        Example(input=f"input_{i}", expected_output=f"expected_{i}") for i in range(n)
    ]


class TestCustomMetricCallback:
    async def test_custom_metric_is_called(self) -> None:
        call_log: list[tuple[str, str]] = []

        def recording_metric(prediction: str, expected: str) -> float:
            call_log.append((prediction, expected))
            return 1.0 if prediction.strip() == expected.strip() else 0.0

        optimizer = PromptOptimizer(llm=_FakeLLM("expected_0"), seed=42)
        await optimizer.optimize(
            template="{input}",
            examples=_make_examples(4),
            metric=recording_metric,
            max_iterations=2,
        )
        assert len(call_log) > 0

    async def test_metric_output_drives_score(self) -> None:
        optimizer = PromptOptimizer(llm=_FakeLLM(), seed=42)
        result = await optimizer.optimize(
            template="{input}",
            examples=_make_examples(4),
            metric=_always_one,
            max_iterations=2,
        )
        assert result.score == 1.0

    async def test_metric_zero_gives_low_score(self) -> None:
        optimizer = PromptOptimizer(llm=_FakeLLM(), seed=42)
        result = await optimizer.optimize(
            template="{input}",
            examples=_make_examples(4),
            metric=_always_zero,
            max_iterations=2,
        )
        assert result.score == 0.0
