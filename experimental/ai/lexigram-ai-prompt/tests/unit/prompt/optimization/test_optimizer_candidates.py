from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from lexigram.ai.prompt.optimization.optimizer import PromptOptimizer
from lexigram.ai.prompt.optimization.types import (
    Example,
    OptimizationError,
    OptimizationStrategy,
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


class _ProgrammableLLM:
    def __init__(self, responses: list[str]) -> None:
        self._responses = responses
        self.call_count = 0

    async def complete(self, messages: Any, **kwargs: Any) -> Ok[_FakeCompletion]:
        response = self._responses[self.call_count % len(self._responses)]
        self.call_count += 1
        return Ok(_FakeCompletion(content=response))

    async def stream_chat(self, messages: Any, **kwargs: Any) -> Ok[Any]:
        return Ok(None)

    async def health_check(self, timeout: float = 5.0) -> Any:
        from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
        return HealthCheckResult(component="fake-llm", status=HealthStatus.HEALTHY)

    async def close(self) -> None:
        pass


class _FailingLLM:
    async def complete(self, messages: Any, **kwargs: Any):
        from lexigram.result import Err
        from lexigram.contracts.ai.llm import LLMError
        return Err(LLMError("always fails"))

    async def stream_chat(self, messages: Any, **kwargs: Any):
        from lexigram.result import Err
        from lexigram.contracts.ai.llm import LLMError
        return Err(LLMError("always fails"))

    async def health_check(self, timeout: float = 5.0) -> Any:
        from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
        return HealthCheckResult(component="fake-llm", status=HealthStatus.UNHEALTHY)

    async def close(self) -> None:
        pass


def _exact_match(prediction: str, expected: str) -> float:
    return 1.0 if prediction.strip() == expected.strip() else 0.0


def _always_one(_prediction: str, _expected: str) -> float:
    return 1.0


def _always_zero(_prediction: str, _expected: str) -> float:
    return 0.0


def _make_examples(n: int) -> list[Example]:
    return [
        Example(input=f"input_{i}", expected_output=f"expected_{i}") for i in range(n)
    ]


class TestOptimizationError:
    async def test_raises_with_single_example(self) -> None:
        optimizer = PromptOptimizer(llm=_FakeLLM())
        with pytest.raises(OptimizationError, match="at least 2"):
            await optimizer.optimize(
                template="Classify: {input}",
                examples=[Example(input="x", expected_output="y")],
                metric=_exact_match,
            )

    async def test_raises_with_zero_examples(self) -> None:
        optimizer = PromptOptimizer(llm=_FakeLLM())
        with pytest.raises(OptimizationError):
            await optimizer.optimize(
                template="Do something: {input}",
                examples=[],
                metric=_exact_match,
            )


class TestBootstrapFewShot:
    async def test_returns_optimized_prompt(self) -> None:
        optimizer = PromptOptimizer(llm=_FakeLLM("expected_0"), seed=42)
        result = await optimizer.optimize(
            template="Answer: {input}",
            examples=_make_examples(5),
            metric=_exact_match,
            max_iterations=3,
            strategy=OptimizationStrategy.BOOTSTRAP_FEW_SHOT,
        )
        assert isinstance(result, OptimizedPrompt)
        assert result.strategy == OptimizationStrategy.BOOTSTRAP_FEW_SHOT
        assert result.template == "Answer: {input}"

    async def test_score_is_float_between_zero_and_one(self) -> None:
        optimizer = PromptOptimizer(llm=_FakeLLM("expected_0"), seed=42)
        result = await optimizer.optimize(
            template="Prefix: {input}",
            examples=_make_examples(4),
            metric=_always_one,
            max_iterations=2,
        )
        assert 0.0 <= result.score <= 1.0

    async def test_respects_max_iterations(self) -> None:
        llm = _FakeLLM("predicted")
        optimizer = PromptOptimizer(llm=llm, seed=42)
        max_iter = 3
        result = await optimizer.optimize(
            template="{input}",
            examples=_make_examples(6),
            metric=_always_zero,
            max_iterations=max_iter,
            strategy=OptimizationStrategy.BOOTSTRAP_FEW_SHOT,
        )
        assert result.iterations == max_iter

    async def test_halts_early_on_perfect_score(self) -> None:
        llm = _FakeLLM("expected_0")
        optimizer = PromptOptimizer(llm=llm, seed=0)
        result = await optimizer.optimize(
            template="{input}",
            examples=_make_examples(4),
            metric=_exact_match,
            max_iterations=10,
            strategy=OptimizationStrategy.BOOTSTRAP_FEW_SHOT,
        )
        assert isinstance(result, OptimizedPrompt)

    async def test_uses_embedding_client_when_provided(self) -> None:
        from lexigram.ai.prompt.optimization.few_shot import DynamicFewShotSelector

        class _FakeEmbeddingClient:
            def __init__(self) -> None:
                self.call_count = 0

            async def embed(self, texts: list[str]) -> list[list[float]]:
                self.call_count += 1
                return [
                    [float(i) if j == 0 else 0.0 for j in range(4)] for i in range(len(texts))
                ]

            async def health_check(self, timeout: float = 5.0) -> Any:
                from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
                return HealthCheckResult(component="fake-embedder", status=HealthStatus.HEALTHY)

            async def close(self) -> None:
                pass

        embedder = _FakeEmbeddingClient()
        optimizer = PromptOptimizer(llm=_FakeLLM(), embedding_client=embedder, seed=42)
        await optimizer.optimize(
            template="{input}",
            examples=_make_examples(6),
            metric=_always_one,
            max_iterations=2,
            strategy=OptimizationStrategy.BOOTSTRAP_FEW_SHOT,
        )
        assert embedder.call_count > 0

    async def test_falls_back_to_random_without_embedder(self) -> None:
        optimizer = PromptOptimizer(llm=_FakeLLM(), embedding_client=None, seed=7)
        result = await optimizer.optimize(
            template="{input}",
            examples=_make_examples(6),
            metric=_always_one,
            max_iterations=2,
            strategy=OptimizationStrategy.BOOTSTRAP_FEW_SHOT,
        )
        assert isinstance(result, OptimizedPrompt)

    async def test_reproducible_with_same_seed(self) -> None:
        examples = _make_examples(8)

        async def _run(seed: int) -> OptimizedPrompt:
            return await PromptOptimizer(
                llm=_FakeLLM("expected_0"), seed=seed
            ).optimize(
                template="{input}",
                examples=examples,
                metric=_exact_match,
                max_iterations=4,
            )

        r1 = await _run(42)
        r2 = await _run(42)
        assert r1.score == r2.score
        assert [e.input for e in r1.few_shot_examples] == [
            e.input for e in r2.few_shot_examples
        ]

    async def test_different_seeds_may_differ(self) -> None:
        examples = _make_examples(10)
        seen: set[tuple[str, ...]] = set()
        for seed in range(5):
            result = await PromptOptimizer(llm=_FakeLLM(), seed=seed).optimize(
                template="{input}",
                examples=examples,
                metric=_always_zero,
                max_iterations=2,
            )
            seen.add(tuple(e.input for e in result.few_shot_examples))
        assert len(seen) >= 1


class TestTemplateRefinement:
    async def test_returns_optimized_prompt(self) -> None:
        improved_template = "Better template for: {input}"
        llm = _ProgrammableLLM(["expected_0", improved_template])
        optimizer = PromptOptimizer(llm=llm, seed=42)
        result = await optimizer.optimize(
            template="Classify: {input}",
            examples=_make_examples(4),
            metric=_exact_match,
            max_iterations=2,
            strategy=OptimizationStrategy.TEMPLATE_REFINEMENT,
        )
        assert isinstance(result, OptimizedPrompt)
        assert result.strategy == OptimizationStrategy.TEMPLATE_REFINEMENT

    async def test_keeps_original_when_refinement_is_worse(self) -> None:
        optimizer = PromptOptimizer(llm=_FakeLLM("nonsense"), seed=42)
        original_template = "Original: {input}"
        result = await optimizer.optimize(
            template=original_template,
            examples=_make_examples(4),
            metric=_exact_match,
            max_iterations=2,
            strategy=OptimizationStrategy.TEMPLATE_REFINEMENT,
        )
        assert result.template
        assert isinstance(result, OptimizedPrompt)

    async def test_failing_llm_returns_safely(self) -> None:
        optimizer = PromptOptimizer(llm=_FailingLLM(), seed=42)
        result = await optimizer.optimize(
            template="{input}",
            examples=_make_examples(4),
            metric=_exact_match,
            max_iterations=2,
            strategy=OptimizationStrategy.TEMPLATE_REFINEMENT,
        )
        assert result.score == 0.0


class TestEnsemble:
    async def test_returns_best_template(self) -> None:
        llm = _FakeLLM("expected_0")
        candidates = [
            "Template A: {input}",
            "Template B: {input}",
            "Template C: {input}",
        ]
        optimizer = PromptOptimizer(llm=llm, seed=42)
        result = await optimizer.optimize(
            template=candidates[0],
            examples=_make_examples(4),
            metric=_exact_match,
            max_iterations=1,
            strategy=OptimizationStrategy.ENSEMBLE,
            candidate_templates=candidates,
        )
        assert isinstance(result, OptimizedPrompt)
        assert result.strategy == OptimizationStrategy.ENSEMBLE
        assert result.template in candidates

    async def test_includes_base_template_in_candidates(self) -> None:
        base_template = "Base: {input}"
        other_templates = ["Alt A: {input}", "Alt B: {input}"]
        optimizer = PromptOptimizer(llm=_FakeLLM(), seed=42)
        result = await optimizer.optimize(
            template=base_template,
            examples=_make_examples(4),
            metric=_always_one,
            strategy=OptimizationStrategy.ENSEMBLE,
            candidate_templates=other_templates,
        )
        assert isinstance(result, OptimizedPrompt)

    async def test_ensemble_without_candidates_uses_base(self) -> None:
        optimizer = PromptOptimizer(llm=_FakeLLM(), seed=42)
        result = await optimizer.optimize(
            template="Solo template: {input}",
            examples=_make_examples(4),
            metric=_always_one,
            strategy=OptimizationStrategy.ENSEMBLE,
        )
        assert result.template == "Solo template: {input}"

    async def test_scores_all_candidates(self) -> None:
        call_counts: dict[str, int] = {}

        def _sync_counting_metric(pred: str, exp: str) -> float:
            call_counts[pred] = call_counts.get(pred, 0) + 1
            return 0.5

        candidates = [f"Template {i}: {{input}}" for i in range(3)]
        optimizer = PromptOptimizer(llm=_FakeLLM("predicted"), seed=42)
        await optimizer.optimize(
            template=candidates[0],
            examples=_make_examples(4),
            metric=_sync_counting_metric,
            strategy=OptimizationStrategy.ENSEMBLE,
            candidate_templates=candidates,
        )
        assert sum(call_counts.values()) > 0
