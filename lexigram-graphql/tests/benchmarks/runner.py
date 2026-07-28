"""GraphQL benchmark runner."""

import asyncio
from collections.abc import Callable
import time
from typing import Any

from lexigram.graphql.tests.benchmarks.result import BenchmarkResult


class Benchmark:
    """Benchmark harness for timing async or sync callables.

    Runs a function repeatedly with an optional warm-up phase and returns
    aggregated timing statistics.
    """

    def __init__(self, name: str) -> None:
        """Initialise the benchmark.

        Args:
            name: Human-readable name for this benchmark.
        """
        self._name = name

    async def run(
        self,
        func: Callable[..., Any],
        iterations: int = 100,
        warmup: int = 10,
    ) -> BenchmarkResult:
        """Run the benchmark function and return aggregate stats.

        Args:
            func: The function (sync or async) to benchmark.
            iterations: Number of timed iterations.
            warmup: Number of untimed warm-up iterations.

        Returns:
            Aggregated benchmark result.
        """
        for _ in range(warmup):
            if asyncio.iscoroutinefunction(func):
                await func()
            else:
                func()

        times: list[float] = []

        for _ in range(iterations):
            start = time.perf_counter()

            if asyncio.iscoroutinefunction(func):
                await func()
            else:
                func()

            end = time.perf_counter()
            times.append(end - start)

        total_time = sum(times)
        avg_time = total_time / iterations
        min_time = min(times)
        max_time = max(times)
        ops_per_second = iterations / total_time if total_time > 0 else 0

        return BenchmarkResult(
            name=self._name,
            iterations=iterations,
            total_time=total_time,
            avg_time=avg_time,
            min_time=min_time,
            max_time=max_time,
            ops_per_second=ops_per_second,
        )


__all__ = [
    "Benchmark",
]
