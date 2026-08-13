"""GraphQL query benchmark suite."""

from typing import Any

from lexigram.logging import get_logger

from lexigram.graphql.tests.benchmarks.result import BenchmarkResult
from lexigram.graphql.tests.benchmarks.runner import Benchmark

logger = get_logger(__name__)


class QueryBenchmark:
    """Benchmark suite for GraphQL query execution.

    Wraps a GraphQL executor and exposes an async ``benchmark()`` method
    that measures query latency over a configurable number of iterations.
    """

    def __init__(self, executor: Any) -> None:
        """Initialise the query benchmark.

        Args:
            executor: GraphQL executor (must expose an async ``execute`` method).
        """
        self._executor = executor
        self._results: list[BenchmarkResult] = []

    async def benchmark(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        iterations: int = 100,
    ) -> BenchmarkResult:
        """Benchmark a single GraphQL query.

        Args:
            query: GraphQL query string.
            variables: Optional query variables.
            iterations: Number of timed iterations.

        Returns:
            Aggregated benchmark result.
        """
        bench = Benchmark(f"Query: {query[:50]}...")

        async def execute() -> None:
            await self._executor.execute(query, variables)

        result = await bench.run(execute, iterations=iterations)
        self._results.append(result)
        return result

    def get_results(self) -> list[BenchmarkResult]:
        """Return all accumulated benchmark results.

        Returns:
            List of results in insertion order.
        """
        return self._results

    def print_summary(self) -> None:
        """Log a summary of all accumulated benchmark results."""
        logger.info("GraphQL Benchmark Results")
        for result in self._results:
            logger.info(
                "%s - Avg: %.2fms, Min: %.2fms, Max: %.2fms, Ops/s: %.2f",
                result.name,
                result.avg_time * 1000,
                result.min_time * 1000,
                result.max_time * 1000,
                result.ops_per_second,
            )


__all__ = [
    "QueryBenchmark",
]
