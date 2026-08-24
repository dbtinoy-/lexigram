from __future__ import annotations

from typing import Any

import pytest

from lexigram.ai.prompt.optimization.few_shot import DynamicFewShotSelector
from lexigram.ai.prompt.optimization.types import Example


class _FakeEmbeddingClient:
    def __init__(self, vectors: list[list[float]] | None = None) -> None:
        self._vectors = vectors
        self.call_count = 0

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.call_count += 1
        if self._vectors is not None:
            n = len(texts)
            result = []
            for i in range(n):
                result.append(self._vectors[i % len(self._vectors)])
            return result
        return [
            [float(i) if j == 0 else 0.0 for j in range(4)] for i in range(len(texts))
        ]

    async def health_check(self, timeout: float = 5.0) -> Any:
        from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
        return HealthCheckResult(component="fake-embedder", status=HealthStatus.HEALTHY)

    async def close(self) -> None:
        pass


class _MappingEmbeddingClient:
    def __init__(
        self, text_to_vec: dict[str, list[float]], fallback_dim: int = 4
    ) -> None:
        self._map = text_to_vec
        self._fallback_dim = fallback_dim
        self.call_count = 0

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.call_count += 1
        result = []
        for i, text in enumerate(texts):
            if text in self._map:
                result.append(self._map[text])
            else:
                vec = [0.0] * self._fallback_dim
                vec[i % self._fallback_dim] = 1.0
                result.append(vec)
        return result

    async def health_check(self, timeout: float = 5.0) -> Any:
        from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
        return HealthCheckResult(component="fake-embedder", status=HealthStatus.HEALTHY)

    async def close(self) -> None:
        pass


def _make_examples(n: int) -> list[Example]:
    return [
        Example(input=f"input_{i}", expected_output=f"expected_{i}") for i in range(n)
    ]


class TestDynamicFewShotSelector:
    async def test_returns_most_similar_examples(self) -> None:
        examples = [
            Example(input="dog", expected_output="animal"),
            Example(input="sky", expected_output="blue"),
            Example(input="cat", expected_output="animal"),
        ]
        embedder = _MappingEmbeddingClient(
            {
                "dog": [1.0, 0.0, 0.0, 0.0],
                "sky": [0.0, 1.0, 0.0, 0.0],
                "cat": [0.0, 0.0, 1.0, 0.0],
                "query": [0.0, 1.0, 0.0, 0.0],
            }
        )
        selector = DynamicFewShotSelector(examples, embedder, max_examples=1)
        selected = await selector.select("query")
        assert len(selected) == 1
        assert selected[0].input == "sky"

    async def test_max_examples_limits_output(self) -> None:
        examples = _make_examples(10)
        embedder = _FakeEmbeddingClient()
        selector = DynamicFewShotSelector(examples, embedder, max_examples=3)
        selected = await selector.select("any query")
        assert len(selected) <= 3

    async def test_empty_examples_returns_empty(self) -> None:
        embedder = _FakeEmbeddingClient()
        selector = DynamicFewShotSelector([], embedder, max_examples=3)
        selected = await selector.select("any query")
        assert selected == []

    async def test_cache_is_populated_on_first_call(self) -> None:
        embedder = _FakeEmbeddingClient()
        examples = _make_examples(4)
        selector = DynamicFewShotSelector(examples, embedder, max_examples=2)

        assert embedder.call_count == 0
        await selector.select("hello")
        assert embedder.call_count >= 1

    async def test_cache_reused_on_second_call(self) -> None:
        embedder = _FakeEmbeddingClient()
        examples = _make_examples(4)
        selector = DynamicFewShotSelector(examples, embedder, max_examples=2)

        await selector.select("first query")
        count_after_first = embedder.call_count

        await selector.select("second query")
        count_after_second = embedder.call_count

        delta = count_after_second - count_after_first
        assert delta <= 1

    async def test_invalidate_cache_forces_re_embed(self) -> None:
        embedder = _FakeEmbeddingClient()
        examples = _make_examples(4)
        selector = DynamicFewShotSelector(examples, embedder, max_examples=2)

        await selector.select("query A")
        count_after_first = embedder.call_count

        selector.invalidate_cache()

        await selector.select("query B")
        count_after_second = embedder.call_count

        delta = count_after_second - count_after_first
        assert delta > 1

    async def test_single_example_returns_it(self) -> None:
        examples = [Example(input="only", expected_output="one")]
        embedder = _FakeEmbeddingClient()
        selector = DynamicFewShotSelector(examples, embedder, max_examples=5)
        selected = await selector.select("query")
        assert len(selected) == 1
        assert selected[0].input == "only"
